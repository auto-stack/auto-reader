#!/usr/bin/env python3
# t02_http_verify.py — READER-001 T-02 阅读状态应用级 HTTP 验证驱动。
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


def main():
    books = curl("GET", "/api/library/books")
    lst = books.get("books", [])
    check(len(lst) >= 1, "at least one book", books)
    b = lst[0]["book_id"]

    # 写入 locator v1 + settings（ASCII 安全传输）
    state = {"book_id": b, "chapter_number": 2, "paragraph_index": 3,
             "quote_prefix": "摇曳碧云斜", "font_size": "large",
             "line_height": "comfy", "updated_at": 0}
    payload = json.dumps(state, ensure_ascii=True)
    w = curl("POST", "/api/library/progress", {"book_id": b, "payload": payload})
    check(w.get("ok") is True, "put progress ok", w)

    g = curl("GET", f"/api/library/progress?book_id={b}")
    check(g.get("chapter_number") == 2, "locator chapter", g)
    check(g.get("paragraph_index") == 3, "locator paragraph", g)
    check(g.get("quote_prefix") == "摇曳碧云斜", "quote_prefix utf8 verbatim (\\u decode)", g)
    check(g.get("font_size") == "large" and g.get("line_height") == "comfy", "settings persisted", g)

    # 覆写 + 再读（最新值语义）
    state2 = {"book_id": b, "chapter_number": 3, "paragraph_index": 0,
              "quote_prefix": "", "font_size": "small", "line_height": "compact", "updated_at": 0}
    w2 = curl("POST", "/api/library/progress", {"book_id": b, "payload": json.dumps(state2, ensure_ascii=True)})
    check(w2.get("ok") is True, "put progress again ok", w2)
    g2 = curl("GET", f"/api/library/progress?book_id={b}")
    check(g2.get("chapter_number") == 3 and g2.get("font_size") == "small", "latest state wins", g2)

    # 错误族
    # 错误消息以纯字符串返回（ok:false 包装仅成功路径保证；错误文本即 body）
    w3 = curl("POST", "/api/library/progress", {"book_id": "nope", "payload": "{\"book_id\":\"nope\"}"})
    check(isinstance(w3, str) and "not found" in w3, "unknown book rejected", w3)
    w4 = curl("POST", "/api/library/progress", {"book_id": b, "payload": "[]"})
    check(isinstance(w4, str) and "JSON object" in w4, "non-object rejected", w4)
    w5 = curl("POST", "/api/library/progress", {"book_id": b, "payload": "{\"book_id\":\"other\"}"})
    check(isinstance(w5, str) and "mismatch" in w5, "id mismatch rejected", w5)
    # 失败写不落盘
    g3 = curl("GET", "/api/library/progress?book_id=nope")
    check(g3 == "", "failed write leaves no record", g3)

    print(f"--- summary: {len(FAILS)} fails ---")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
