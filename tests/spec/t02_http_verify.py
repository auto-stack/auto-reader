#!/usr/bin/env python3
# t02_http_verify.py — READER-001 T-02 阅读状态应用级 HTTP 验证驱动。
# Phase 3（F-08/F-09/F-10 修复后）：body = {book_id, payload, para_text}；
# payload 经 jsonx 词法门（结构/类型精确/重复键拒绝/空白与转义键兼容）；
# para_text 为顶层内容锚点（段级定位必填、与原文行逐字核对，等长替换在
# 保存时被拒）；错误统一 {"ok":false,"message"}。
# 前置：app 以 VM 后端在 127.0.0.1:17825 运行（书库已至少有 1 本书）。
# 传输纪律（T-02 实测）：写端点请求体必须 ASCII 安全（\u 转义，标准
# JSON）；VM HTTP 层存在「快处理器空响应体」竞态（T-00 报告）——本驱动
# 经 subprocess 调 curl（每请求新连接的可靠客户端）+ 空响应重试。
# 用法：python tests/spec/t02_http_verify.py
import json
import subprocess
import sys

BASE = "http://127.0.0.1:17825"
FAILS = []


def curl(method, path, body=None, tries=3):
    for k in range(tries):
        cmd = ["curl", "-s", "-m", "15", "-X", method]
        if body is not None:
            cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(body, ensure_ascii=True)]
        cmd.append(BASE + path)
        out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8").stdout
        if out.strip():
            v = json.loads(out)
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

    # 取第一章原文行，选首个非空行作锚点（段级定位须与 para_text 逐字一致）
    ch = curl("GET", f"/api/library/chapter?book_id={b}&number=1")
    check(ch.get("title", "") not in ("", "内容缺失", "章节不存在"), "chapter 1 readable", ch)
    body = ch.get("body", "")
    lines = body.split("\n")
    pi = next((i for i, t in enumerate(lines) if t.strip()), -1)
    check(pi >= 0, "chapter 1 has a non-empty paragraph", body)
    anchor = lines[pi].strip()

    def state(p_index, sig, font="large", line="comfy"):
        return {"book_id": b, "chapter_number": 1, "paragraph_index": p_index,
                "para_hash": sig, "font_size": font, "line_height": line, "updated_at": 0}

    # 写入 locator v1 + 内容锚点（ASCII 安全传输；锚点=该行全文）
    w = curl("POST", "/api/library/progress", {"book_id": b, "payload": json.dumps(state(pi, f"sig1:{len(anchor)}:1"), ensure_ascii=True), "para_text": anchor})
    check(w.get("ok") is True, "put progress ok (content anchor)", w)

    g = curl("GET", f"/api/library/progress?book_id={b}")
    check(g.get("chapter_number") == 1, "locator chapter", g)
    check(g.get("paragraph_index") == pi, "locator paragraph", g)
    check(g.get("para_text") == anchor, "content anchor verbatim (\\u decode)", g)
    check(g.get("font_size") == "large" and g.get("line_height") == "comfy", "settings persisted", g)

    # F-09: 合法 JSON 空白（属性名与冒号间）必须兼容
    spaced = json.dumps(state(pi, f"sig1:{len(anchor)}:1"), ensure_ascii=True).replace('":', '" :')
    w_sp = curl("POST", "/api/library/progress", {"book_id": b, "payload": spaced, "para_text": anchor})
    check(w_sp.get("ok") is True, "F-09 whitespace before colon accepted", w_sp)

    # F-09: 数字字符串冒充整数必须拒绝
    wrong_type = state(pi, f"sig1:{len(anchor)}:1")
    wrong_type["chapter_number"] = "1"
    wrong_type["paragraph_index"] = str(pi)
    wrong_type["updated_at"] = "0"
    w_type = curl("POST", "/api/library/progress", {"book_id": b, "payload": json.dumps(wrong_type, ensure_ascii=True), "para_text": anchor})
    check(w_type.get("ok") is False, "F-09 numeric strings rejected", w_type)

    # F-09: 重复键拒绝
    dup = '{"book_id":"%s","book_id":"%s","chapter_number":1,"paragraph_index":%d,"para_hash":"sig1:1:1","font_size":"medium","line_height":"comfy","updated_at":0}' % (b, b, pi)
    w_dup = curl("POST", "/api/library/progress", {"book_id": b, "payload": dup, "para_text": anchor})
    check(w_dup.get("ok") is False, "F-09 duplicate key rejected", w_dup)

    # F-08: 等长替换后旧内容锚点拒绝；新内容重新锚定成功
    oob = state(0, "sig1:3:1")
    oob["paragraph_index"] = pi
    fake = "x" * len(anchor) if anchor != "x" * len(anchor) else "y" * len(anchor)
    w_stale = curl("POST", "/api/library/progress", {"book_id": b, "payload": json.dumps(oob, ensure_ascii=True), "para_text": fake})
    check(w_stale.get("ok") is False, "F-08 stale equal-length anchor rejected", w_stale)
    w_re = curl("POST", "/api/library/progress", {"book_id": b, "payload": json.dumps(oob, ensure_ascii=True), "para_text": anchor})
    check(w_re.get("ok") is True, "F-08 re-anchor with live content accepted", w_re)

    # F-10: emoji 段锚点（UTF-16 口径的 sig1 兼容位 + para_text 内容核对）
    emoji_line = next((i for i, t in enumerate(lines) if "\U0001F600" in t), None)
    if emoji_line is None:
        print("SKIP F-10 emoji case (fixture has no emoji paragraph)")
    else:
        et = lines[emoji_line].strip()
        w_emo = curl("POST", "/api/library/progress", {"book_id": b, "payload": json.dumps(state(emoji_line, "sig1:%d:1" % (len(et) + 1), ensure_ascii=True), ensure_ascii=True), "para_text": et})
        check(w_emo.get("ok") is True, "F-10 emoji paragraph anchor accepted", w_emo)

    # 章级书签（pi=-1，免内容锚点）+ 最新值语义
    w2 = curl("POST", "/api/library/progress", {"book_id": b, "payload": json.dumps(state(-1, "sig1:0:1", font="small", line="compact"), ensure_ascii=True), "para_text": ""})
    check(w2.get("ok") is True, "put chapter bookmark ok", w2)
    g2 = curl("GET", f"/api/library/progress?book_id={b}")
    check(g2.get("font_size") == "small" and g2.get("paragraph_index") == -1, "latest state wins", g2)

    # 错误族：统一 {"ok":false,"message"}
    def err_name(resp):
        if isinstance(resp, dict):
            return resp.get("message", "") or resp.get("error", "")
        return str(resp)

    w3 = curl("POST", "/api/library/progress", {"book_id": "nope", "payload": json.dumps(state(-1, "sig1:0:1"), ensure_ascii=True), "para_text": ""})
    check(isinstance(w3, dict) and w3.get("ok") is False and "not found" in err_name(w3), "unknown book rejected", w3)
    w4 = curl("POST", "/api/library/progress", {"book_id": b, "payload": "[]", "para_text": ""})
    check(isinstance(w4, dict) and w4.get("ok") is False and "JSON object" in err_name(w4), "non-object rejected", w4)
    w5 = curl("POST", "/api/library/progress", {"book_id": b, "payload": json.dumps({"book_id": "other", "chapter_number": 1, "paragraph_index": -1, "para_hash": "sig1:0:1", "font_size": "medium", "line_height": "comfy", "updated_at": 0}, ensure_ascii=True), "para_text": ""})
    check(isinstance(w5, dict) and w5.get("ok") is False and "mismatch" in err_name(w5), "id mismatch rejected", w5)
    w6 = curl("POST", "/api/library/progress", {"book_id": b, "payload": '{"book_id":"' + b + '",', "para_text": ""})
    check(isinstance(w6, dict) and w6.get("ok") is False, "truncated JSON rejected", w6)
    hidden = {"book_id": "wrong", "note": b, "chapter_number": 1, "paragraph_index": -1,
              "para_hash": "sig1:0:1", "font_size": "medium", "line_height": "comfy", "updated_at": 0}
    w7 = curl("POST", "/api/library/progress", {"book_id": b, "payload": json.dumps(hidden, ensure_ascii=True), "para_text": ""})
    check(isinstance(w7, dict) and w7.get("ok") is False and "mismatch" in err_name(w7), "hidden-id mismatch rejected", w7)
    oob_ch = dict(state(-1, "sig1:0:1"), chapter_number=99)
    w8 = curl("POST", "/api/library/progress", {"book_id": b, "payload": json.dumps(oob_ch, ensure_ascii=True), "para_text": ""})
    check(isinstance(w8, dict) and w8.get("ok") is False and "range" in err_name(w8), "chapter out of range rejected", w8)
    p999 = state(999, "sig1:999:1")
    w9 = curl("POST", "/api/library/progress", {"book_id": b, "payload": json.dumps(p999, ensure_ascii=True), "para_text": "任意"})
    check(isinstance(w9, dict) and w9.get("ok") is False and "range" in err_name(w9), "paragraph 999 out of range rejected", w9)
    if pi >= 0:
        bad_anchor = state(pi, "sig1:1:1")
        w10 = curl("POST", "/api/library/progress", {"book_id": b, "payload": json.dumps(bad_anchor, ensure_ascii=True), "para_text": anchor})
        # 与上一有效态同内容锚点（anchor==live）→ 成功；构造失配：换一段的文本
        other = next((t.strip() for i, t in enumerate(lines) if i != pi and t.strip()), anchor + "x")
        w10 = curl("POST", "/api/library/progress", {"book_id": b, "payload": json.dumps(state(pi, "sig1:1:1"), ensure_ascii=True), "para_text": other})
        check(isinstance(w10, dict) and w10.get("ok") is False and "anchor" in err_name(w10), "anchor mismatch rejected", w10)

    # 失败写不落盘 + 最新有效状态保留
    g3 = curl("GET", "/api/library/progress?book_id=nope")
    check(g3 == "", "failed write leaves no record", g3)
    w_bm = curl("POST", "/api/library/progress", {"book_id": b, "payload": json.dumps(state(-1, "sig1:0:1", font="small", line="compact"), ensure_ascii=True), "para_text": ""})
    check(w_bm.get("ok") is True, "bookmark re-established", w_bm)
    g4 = curl("GET", f"/api/library/progress?book_id={b}")
    check(g4.get("font_size") == "small" and g4.get("paragraph_index") == -1, "last valid state verbatim after failures", g4)

    print(f"--- summary: {len(FAILS)} fails ---")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
