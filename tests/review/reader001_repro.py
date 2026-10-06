"""READER-001 review reproductions; only run against a disposable VM server.

AUTO_READER_DATA must be the same isolated directory used by the server.
Run: python tests/review/reader001_repro.py
Fails until the Phase 2 corrections are implemented. Does not touch user books.
"""
import json
import os
from pathlib import Path
import tempfile
import urllib.error
import urllib.request
import uuid

BASE = os.environ.get("REVIEW_BASE", "http://127.0.0.1:17825")
DATA = Path(os.environ["AUTO_READER_DATA"])
if not DATA.is_dir() or not DATA.name.startswith("reader001-review-"):
    raise SystemExit("AUTO_READER_DATA must be an existing disposable reader001-review-* directory")
WORK = Path(tempfile.mkdtemp(prefix="reader001-review-repro-"))
RESULTS = []


def req(method, path, body=None, ascii_safe=True):
    data = None if body is None else json.dumps(body, ensure_ascii=ascii_safe).encode()
    r = urllib.request.Request(BASE + path, data=data, method=method)
    if data is not None:
        r.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(r, timeout=30) as response:
        result = json.loads(response.read())
    return json.loads(result) if isinstance(result, str) and result else result


def record(name, correct, evidence):
    RESULTS.append({"case": name, "result": "pass" if correct else "fail", "evidence": evidence})


def imp(path, force=False, ascii_safe=True):
    return req("POST", "/api/library/import", {"path": str(path), "author": "review", "force": force}, ascii_safe)


def main():
    # Deliberate equal-size, equal-prefix collision, without a probabilistic search.
    prefix = uuid.uuid4().hex + "A" * 64
    text_a, text_b = prefix + "first\n", prefix + "other\n"
    a, b = WORK / "a.txt", WORK / "b.txt"
    a.write_text(text_a, encoding="utf-8")
    b.write_text(text_b, encoding="utf-8")
    first = imp(a)
    second = imp(b)
    record("F-02 different tails must not deduplicate", second.get("code") == "ok", second)
    forced = imp(b, True)
    bid = forced["book_id"]
    chapter = req("GET", f"/api/library/chapter?book_id={bid}&number=1")
    record("F-02 force must preserve second source", chapter.get("body") == text_b.strip(), {"body": chapter.get("body"), "expected": text_b.strip()})

    # Existing orphan/corrupted asset must be checked before accepting its reuse.
    original = req("GET", f"/api/library/books/{first['book_id']}")
    managed = Path(original["managed_path"])
    saved = managed.read_bytes()
    try:
        managed.write_bytes(b"")
        imported = imp(a, True)
        rec = req("GET", f"/api/library/books/{imported['book_id']}")
        record("F-03 corrupt managed copy must not report success", imported.get("code") != "ok" or Path(rec["managed_path"]).read_bytes() == saved, {"outcome": imported, "managed_size": managed.stat().st_size})
    finally:
        managed.write_bytes(saved)

    # JSON validation currently searches substrings instead of parsing a schema.
    for name, payload in [
        ("F-04 malformed ReadingState must be rejected", '{"book_id":"' + bid + '",'),
        ("F-04 mismatched ReadingState must be rejected", json.dumps({"book_id": "wrong", "note": bid})),
    ]:
        try:
            outcome = req("POST", "/api/library/progress", {"book_id": bid, "payload": payload})
            record(name, not (isinstance(outcome, dict) and outcome.get("ok")), outcome)
        except urllib.error.HTTPError as error:
            record(name, True, {"status": error.code})

    # Reproduce browser JSON.stringify's raw UTF-8 body with a Chinese pathname.
    chinese = WORK / "中文书.txt"
    chinese.write_text(uuid.uuid4().hex + "\n中文正文。\n", encoding="utf-8")
    outcome = imp(chinese, ascii_safe=False)
    record("C-01 Unicode import path must work", outcome.get("code") == "ok", outcome)

    lp = DATA / "library.json"
    saved_index = lp.read_bytes()
    bak = DATA / "library.json.bak"
    saved_bak = bak.read_bytes() if bak.is_file() else None
    c = WORK / "index-check.txt"
    c.write_text(uuid.uuid4().hex + "\n", encoding="utf-8")
    try:
        lp.write_bytes(b"")
        outcome = imp(c)
        record("F-06 empty existing index must not be replaced", outcome.get("code") != "ok" and lp.read_bytes() == b"", outcome)
        lp.write_bytes(saved_index)
        if bak.exists():
            bak.unlink()
        bak.mkdir()
        outcome = imp(c)
        record("F-06 backup failure must abort index mutation", outcome.get("code") != "ok" and lp.read_bytes() == saved_index, outcome)
    finally:
        lp.write_bytes(saved_index)
        if bak.is_dir():
            bak.rmdir()
        if saved_bak is not None:
            bak.write_bytes(saved_bak)

    # UI review fixture: valid saved location, invalid paragraph and stale quote.
    ui = WORK / "ui-location.txt"
    ui.write_text("第一章 开始\n第一段。\n第二段。\n第二章 后续\n第三段。\n", encoding="utf-8")
    ui_id = imp(ui)["book_id"]
    state = {"book_id": ui_id, "chapter_number": 1, "paragraph_index": 999, "para_hash": "sig1:999:1", "font_size": "medium", "line_height": "comfy", "updated_at": 0}
    req("POST", "/api/library/progress", {"book_id": ui_id, "payload": json.dumps(state), "para_text": "任意"})
    print(json.dumps({"results": RESULTS, "ui_id": ui_id, "work": str(WORK)}, ensure_ascii=True, indent=2))
    return int(any(r["result"] == "fail" for r in RESULTS))


if __name__ == "__main__":
    raise SystemExit(main())
