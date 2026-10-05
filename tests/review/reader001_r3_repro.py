"""Independent r3 review probes. Use only a reader001-review-* VM test library."""
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


def put(bid, payload):
    return req("POST", "/api/library/progress", {"book_id": bid, "payload": payload})


def main():
    src = WORK / "anchor.txt"
    src.write_text("第一章 " + uuid.uuid4().hex + "\nAAA\nA😀B\n", encoding="utf-8")
    bid = imp(src)["book_id"]
    valid = state(bid)
    initial = put(bid, json.dumps(valid))
    assert initial.get("ok") is True, initial

    # All values are valid; whitespace between a property name and ':' is JSON.
    spaced = json.dumps(valid).replace('":', '" :')
    outcome = put(bid, spaced)
    record("F-09 valid JSON with whitespace before colon", outcome.get("ok") is True, outcome)

    # Strict integer schema must reject numeric strings, not coerce them.
    wrong_type = dict(valid, chapter_number="1", paragraph_index="0", updated_at="0")
    outcome = put(bid, json.dumps(wrong_type))
    record("F-09 numeric strings must be rejected", outcome.get("ok") is False, outcome)

    # Vue String.length uses UTF-16 code units; astral character is 2 units.
    emoji = state(bid, 1, "sig1:4:1")
    outcome = put(bid, json.dumps(emoji))
    record("F-10 Vue signature of an emoji paragraph must save", outcome.get("ok") is True, outcome)

    # Reset valid bookmark then change text without changing its length.
    assert put(bid, json.dumps(valid)).get("ok") is True
    rec = req("GET", f"/api/library/books/{bid}")
    asset = Path(rec["managed_path"])
    asset.write_text(src.read_text(encoding="utf-8").replace("AAA", "BBB"), encoding="utf-8")
    outcome = put(bid, json.dumps(valid))
    record("F-08 changed equal-length paragraph must invalidate old anchor", outcome.get("ok") is False, {"outcome": outcome, "old_text": "AAA", "current_text": "BBB", "saved_signature": valid["para_hash"]})

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
    assert put(long_id, json.dumps(long_state)).get("ok") is True
    result = {"results": RESULTS, "same_length_book_id": bid, "viewport_book_id": long_id, "work": str(WORK)}
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return int(any(x["result"] == "fail" for x in RESULTS))


if __name__ == "__main__":
    raise SystemExit(main())
