#!/usr/bin/env python3
# t02_http_verify.py — READER-001 T-02 阅读状态应用级 HTTP 验证驱动。
# Phase 2（F-04 修复后）：错误响应统一 {"ok":false,"message"} 字典；
# 写入需通过 schema 强校验（真实 JSON 解析、book_id 严格相等、章段范围、
# para_hash 原文锚点、settings 枚举、键重复拒绝）；读侧容错。
# 前置：app 以 VM 后端在 127.0.0.1:17825 运行（书库已至少有 1 本书）。
# 传输纪律（T-02 实测）：写端点请求体必须 ASCII 安全（\u 转义，标准
# JSON）；VM HTTP 层存在「快处理器空响应体」竞态（缺陷已登记 T-00
# 报告 §13）——本驱动经 subprocess 调 curl（实测可靠的客户端）。
# 用法：python tests/spec/t02_http_verify.py
import json
import subprocess
import sys

BASE = "http://127.0.0.1:17825"
FAILS = []


def curl(method, path, body=None, tries=3):
    # VM HTTP 层存在「快处理器空响应体」竞态（T-00 报告 §13）——本驱动的
    # 写操作均为幂等保存，空响应重试（上限 3 次）。
    for k in range(tries):
        cmd = ["curl", "-s", "-m", "15", "-X", method]
        if body is not None:
            cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(body, ensure_ascii=True)]
        cmd.append(BASE + path)
        out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8").stdout
        if out.strip():
            v = json.loads(out)
            # str 返回端点双层编码（spec 增量）；纯文本错误消息不是 JSON
            if isinstance(v, str):
                try:
                    v2 = json.loads(v)
                    if isinstance(v2, (dict, list)):
                        return v2
                except (json.JSONDecodeError, ValueError):
                    pass
                return v
            return v
        import time
        time.sleep(0.3)
    return {"__empty__": True}


def check(cond, name, detail=""):
    if cond:
        print("PASS " + name)
    else:
        FAILS.append(name)
        print("FAIL " + name + (" :: " + str(detail)[:300] if detail else ""))


def line_sig(text):
    # 锚点签名（字符口径；后端双口径接受字节/字符两种计数值）
    t = text.strip()
    return f"sig1:{len(t)}:1"


def main():
    books = curl("GET", "/api/library/books")
    lst = books.get("books", [])
    check(len(lst) >= 1, "at least one book", books)
    b = lst[0]["book_id"]

    # 取第一章原文行，选首个非空行作锚点（schema 要求段级定位指向非空行）
    ch = curl("GET", f"/api/library/chapter?book_id={b}&number=1")
    check(ch.get("title", "") not in ("", "内容缺失", "章节不存在"), "chapter 1 readable", ch)
    body = ch.get("body", "")
    lines = body.split("\n")
    pi = next((i for i, t in enumerate(lines) if t.strip()), -1)
    check(pi >= 0, "chapter 1 has a non-empty paragraph", body)

    # 写入 locator v1 + settings（ASCII 安全传输；锚点 = 非空行签名）
    state = {"book_id": b, "chapter_number": 1, "paragraph_index": pi,
             "para_hash": line_sig(lines[pi]),
             "quote_prefix": "摇曳碧云斜", "font_size": "large",
             "line_height": "comfy", "updated_at": 0}
    payload = json.dumps(state, ensure_ascii=True)
    w = curl("POST", "/api/library/progress", {"book_id": b, "payload": payload})
    check(w.get("ok") is True, "put progress ok", w)

    g = curl("GET", f"/api/library/progress?book_id={b}")
    check(g.get("chapter_number") == 1, "locator chapter", g)
    check(g.get("paragraph_index") == pi, "locator paragraph", g)
    check(g.get("para_hash") == line_sig(lines[pi]), "anchor verbatim", g)
    check(g.get("quote_prefix") == "摇曳碧云斜", "quote_prefix utf8 verbatim (\\u decode)", g)
    check(g.get("font_size") == "large" and g.get("line_height") == "comfy", "settings persisted", g)

    # 覆写 + 再读（最新值语义；章级书签形态 pi=-1 免锚点）
    state2 = {"book_id": b, "chapter_number": 1, "paragraph_index": -1,
              "para_hash": "sig1:0:1", "quote_prefix": "", "font_size": "small",
              "line_height": "compact", "updated_at": 0}
    w2 = curl("POST", "/api/library/progress", {"book_id": b, "payload": json.dumps(state2, ensure_ascii=True)})
    check(w2.get("ok") is True, "put progress again ok", w2)
    g2 = curl("GET", f"/api/library/progress?book_id={b}")
    check(g2.get("font_size") == "small" and g2.get("paragraph_index") == -1, "latest state wins", g2)

    # 错误族：统一 {"ok":false,"message"}（F-04 起与成功响应同构）
    def err_name(resp):
        if isinstance(resp, dict):
            return resp.get("message", "")
        return str(resp)

    w3 = curl("POST", "/api/library/progress", {"book_id": "nope", "payload": json.dumps({"book_id": "nope", "chapter_number": 1, "paragraph_index": -1, "para_hash": "sig1:0:1", "font_size": "medium", "line_height": "comfy", "updated_at": 0})})
    check(isinstance(w3, dict) and w3.get("ok") is False and "not found" in err_name(w3), "unknown book rejected", w3)
    w4 = curl("POST", "/api/library/progress", {"book_id": b, "payload": "[]"})
    check(isinstance(w4, dict) and w4.get("ok") is False and "JSON object" in err_name(w4), "non-object rejected", w4)
    w5 = curl("POST", "/api/library/progress", {"book_id": b, "payload": json.dumps({"book_id": "other", "chapter_number": 1, "paragraph_index": -1, "para_hash": "sig1:0:1", "font_size": "medium", "line_height": "comfy", "updated_at": 0})})
    check(isinstance(w5, dict) and w5.get("ok") is False and "mismatch" in err_name(w5), "id mismatch rejected", w5)
    w6 = curl("POST", "/api/library/progress", {"book_id": b, "payload": '{"book_id":"' + b + '",'})
    check(isinstance(w6, dict) and w6.get("ok") is False and "JSON" in err_name(w6), "truncated JSON rejected", w6)
    hidden = {"book_id": "wrong", "note": b, "chapter_number": 1, "paragraph_index": -1,
              "para_hash": "sig1:0:1", "font_size": "medium", "line_height": "comfy", "updated_at": 0}
    w7 = curl("POST", "/api/library/progress", {"book_id": b, "payload": json.dumps(hidden)})
    check(isinstance(w7, dict) and w7.get("ok") is False and "mismatch" in err_name(w7), "hidden-id mismatch rejected", w7)
    oob = {"book_id": b, "chapter_number": 99, "paragraph_index": -1,
           "para_hash": "sig1:0:1", "font_size": "medium", "line_height": "comfy", "updated_at": 0}
    w8 = curl("POST", "/api/library/progress", {"book_id": b, "payload": json.dumps(oob)})
    check(isinstance(w8, dict) and w8.get("ok") is False and "range" in err_name(w8), "chapter out of range rejected", w8)
    p999 = {"book_id": b, "chapter_number": 1, "paragraph_index": 999,
            "para_hash": "sig1:999:1", "font_size": "medium", "line_height": "comfy", "updated_at": 0}
    w9 = curl("POST", "/api/library/progress", {"book_id": b, "payload": json.dumps(p999)})
    check(isinstance(w9, dict) and w9.get("ok") is False and "range" in err_name(w9), "paragraph 999 out of range rejected", w9)
    bad_anchor = {"book_id": b, "chapter_number": 1, "paragraph_index": pi,
                  "para_hash": "sig1:1:1", "font_size": "medium", "line_height": "comfy", "updated_at": 0}
    w10 = curl("POST", "/api/library/progress", {"book_id": b, "payload": json.dumps(bad_anchor)})
    check(isinstance(w10, dict) and w10.get("ok") is False and "anchor" in err_name(w10), "anchor mismatch rejected", w10)

    # 失败写不落盘 + 最新有效状态保留
    g3 = curl("GET", "/api/library/progress?book_id=nope")
    check(g3 == "", "failed write leaves no record", g3)
    g4 = curl("GET", f"/api/library/progress?book_id={b}")
    check(g4 == json.loads(json.dumps(state2)), "last valid state verbatim after failures", g4)

    print(f"--- summary: {len(FAILS)} fails ---")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
