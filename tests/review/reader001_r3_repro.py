"""Independent r3 review probes, evolved to the Phase 3 contract (r4 work).

Phase 3 契约变化（计划 §5 T-11/T-12）：POST /api/library/progress 的 body
新增顶层 para_text 内容锚点字段——段级定位（paragraph_index>=0）必填，且
后端与当前原文行逐字核对后才落盘；内层 payload 夹带 para_text 被拒绝；
旧 sig1-only 锚点（无 para_text）不再可作为段级定位保存。原 r3 反例在本
契约下的等价形态与本文件为准（F-10 的"Vue 长度签名"案例改为 emoji 段
经真实内容锚点保存成功；F-08 的等长替换语义不变）。

Use only a reader001-review-* VM test library.
"""
import json
import os
from pathlib import Path
import tempfile
import urllib.request
import uuid

DATA = Path(os.environ["AUTO_READER_DATA"])
assert DATA.is_dir() and DATA.name.startswith("reader001-review-")
BASE = os.environ.get("REVIEW_BASE", "http://127.0.0.1:17825")
WORK = Path(tempfile.mkdtemp(prefix="reader001-review-r3-"))
RESULTS = []


def req(method, path, body=None):
    data = None if body is None else json.dumps(body, ensure_ascii=True).encode()
    r = urllib.request.Request(BASE + path, data=data, method=method)
    if data is not None:
        r.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(r, timeout=30) as resp:
        out = json.loads(resp.read())
    return json.loads(out) if isinstance(out, str) and out else out


def imp(path):
    return req("POST", "/api/library/import", {"path": str(path), "author": "review-r3", "force": False})


def record(name, correct, evidence):
    RESULTS.append({"case": name, "result": "pass" if correct else "fail", "evidence": evidence})


def state(bid, paragraph=0, sig="sig1:3:1"):
    return {"book_id": bid, "chapter_number": 1, "paragraph_index": paragraph, "para_hash": sig, "font_size": "medium", "line_height": "comfy", "updated_at": 0}


def put(bid, payload, para_text=None):
    # para_text 恒在（缺省 ""）：字段整体缺失会被框架绑定层以 400 拒绝，
    # 而空串走库级「缺内容锚点」拒绝语义——本驱动验证后者。
    import urllib.error
    body = {"book_id": bid, "payload": payload, "para_text": para_text or ""}
    try:
        return req("POST", "/api/library/progress", body)
    except urllib.error.HTTPError as error:
        return {"ok": False, "message": f"HTTP {error.code}", "error": True}


def main():
    src = WORK / "anchor.txt"
    src.write_text("第一章 " + uuid.uuid4().hex + "\nAAA\nA😀B\n", encoding="utf-8")
    bid = imp(src)["book_id"]
    valid = state(bid)

    # Phase 3 契约：段级保存必须携带与原文行逐字相等的内容锚点。
    initial = put(bid, json.dumps(valid), "AAA")
    assert initial.get("ok") is True, initial

    # All values are valid; whitespace between a property name and ':' is JSON.
    spaced = json.dumps(valid).replace('":', '" :')
    outcome = put(bid, spaced, "AAA")
    record("F-09 valid JSON with whitespace before colon", outcome.get("ok") is True, outcome)

    # Strict integer schema must reject numeric strings, not coerce them.
    wrong_type = dict(valid, chapter_number="1", paragraph_index="0", updated_at="0")
    outcome = put(bid, json.dumps(wrong_type), "AAA")
    record("F-09 numeric strings must be rejected", outcome.get("ok") is False, outcome)

    # Duplicate keys must be rejected at the lexical gate.
    dup_raw = '{"book_id":"%s","book_id":"%s","chapter_number":1,"paragraph_index":0,"para_hash":"sig1:3:1","font_size":"medium","line_height":"comfy","updated_at":0}' % (bid, bid)
    outcome = put(bid, dup_raw, "AAA")
    record("F-09 duplicate keys must be rejected", outcome.get("ok") is False, outcome)

    # Legacy sig1-only anchor without content evidence cannot claim a paragraph.
    outcome = put(bid, json.dumps(valid))
    record("Phase 3 sig1-only paragraph anchor rejected", outcome.get("ok") is False, outcome)

    # Inner-payload para_text smuggling is rejected (anchor is top-level only).
    smuggled = dict(valid, para_text="AAA")
    outcome = put(bid, json.dumps(smuggled), "AAA")
    record("Phase 3 para_text inside payload rejected", outcome.get("ok") is False, outcome)

    # Astral (emoji) paragraph saves through its verbatim content anchor.
    emoji = state(bid, 1, "sig1:4:1")
    outcome = put(bid, json.dumps(emoji), "A😀B")
    record("F-10 emoji paragraph saves via content anchor", outcome.get("ok") is True, outcome)
    stored = req("GET", f"/api/library/progress?book_id={bid}")
    record("F-10 emoji anchor stored verbatim", stored.get("para_text") == "A😀B", stored)

    # Reset valid bookmark then change text without changing its length.
    assert put(bid, json.dumps(valid), "AAA").get("ok") is True
    rec = req("GET", f"/api/library/books/{bid}")
    asset = Path(rec["managed_path"])
    asset.write_text(src.read_text(encoding="utf-8").replace("AAA", "BBB"), encoding="utf-8")
    outcome = put(bid, json.dumps(valid), "AAA")
    record("F-08 changed equal-length paragraph must invalidate old anchor", outcome.get("ok") is False, {"outcome": outcome, "old_text": "AAA", "current_text": "BBB", "saved_anchor": "AAA"})
    outcome = put(bid, json.dumps(valid), "BBB")
    record("F-08 re-anchor to live content accepted", outcome.get("ok") is True, outcome)

    # Missing/invalid index shapes must never be interpreted as a fresh library.
    lp = DATA / "library.json"
    saved = lp.read_bytes()
    check_src = WORK / "schema.txt"
    check_src.write_text(uuid.uuid4().hex, encoding="utf-8")
    try:
        for shape in [None, {}, []]:
            invalid = {"version": 1, "books": shape}
            if shape == []:
                invalid["version"] = "1"
            raw = json.dumps(invalid).encode()
            lp.write_bytes(raw)
            outcome = imp(check_src)
            record("index shape " + json.dumps(invalid), outcome.get("code") != "ok" and lp.read_bytes() == raw, outcome)
            lp.write_bytes(saved)
    finally:
        lp.write_bytes(saved)

    # Browser fixture: target paragraph far below the initial viewport.
    long = WORK / "viewport.txt"
    marker = uuid.uuid4().hex
    lines = ["第一章 " + marker] + [f"段落{i:03d} {marker}" for i in range(100)]
    long.write_text("\n".join(lines), encoding="utf-8")
    long_id = imp(long)["book_id"]
    long_state = state(long_id, 80, "sig1:" + str(len(lines[81])) + ":1")
    ok80 = put(long_id, json.dumps(long_state), lines[81])
    assert ok80.get("ok") is True, ok80
    result = {"results": RESULTS, "same_length_book_id": bid, "viewport_book_id": long_id, "work": str(WORK)}
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return int(any(x["result"] == "fail" for x in RESULTS))


if __name__ == "__main__":
    raise SystemExit(main())
