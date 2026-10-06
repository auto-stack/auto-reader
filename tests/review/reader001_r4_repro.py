"""Independent r4 controls; only a disposable reader001-review-* VM library."""
import json
import os
from pathlib import Path
import tempfile
import urllib.request
import uuid

DATA = Path(os.environ["AUTO_READER_DATA"])
assert DATA.is_dir() and DATA.name.startswith("reader001-review-")
BASE = os.environ.get("REVIEW_BASE", "http://127.0.0.1:17825")
WORK = Path(tempfile.mkdtemp(prefix="reader001-review-r4-"))
RESULTS = []


def req(method, path, body=None):
    data = None if body is None else json.dumps(body, ensure_ascii=True).encode()
    request = urllib.request.Request(BASE + path, data=data, method=method)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read())
    return json.loads(result) if isinstance(result, str) and result else result


def record(case, correct, evidence):
    RESULTS.append(dict(case=case, result="pass" if correct else "fail", evidence=evidence))


def import_lines(name, lines):
    source = WORK / (name + ".txt")
    source.write_text("第一章 " + uuid.uuid4().hex + "\n" + "\n".join(lines), encoding="utf-8")
    result = req("POST", "/api/library/import", dict(path=str(source), author="review-r4", force=False))
    assert result["code"] == "ok", result
    return result["book_id"]


def state(bid, pi=0):
    return dict(book_id=bid, chapter_number=1, paragraph_index=pi, para_hash="sig1:1:1",
                font_size="medium", line_height="comfy", updated_at=0)


def put(bid, saved, anchor):
    return req("POST", "/api/library/progress", dict(book_id=bid, payload=json.dumps(saved), para_text=anchor))


def main():
    undefined_id = import_lines("literal-undefined", ["undefined", "normal"])
    outcome = put(undefined_id, state(undefined_id), "undefined")
    record("literal undefined content saves", outcome.get("ok") is True, outcome)
    saved = req("GET", "/api/library/progress?book_id=" + undefined_id)
    record("literal undefined content persists", saved.get("para_text") == "undefined", saved)

    corrupt_id = import_lines("invalid-reading-state", ["normal", "second"])
    assert put(corrupt_id, state(corrupt_id), "normal").get("ok") is True
    rp = DATA / "reading" / (corrupt_id + ".json")
    original_state = rp.read_bytes()
    try:
        variants = [dict(state(corrupt_id), chapter_number="1", paragraph_index="0", para_text="normal"),
                    dict(state("another-book"), para_text="normal"),
                    dict(book_id=corrupt_id)]
        for variant in variants:
            raw = json.dumps(variant).encode()
            rp.write_bytes(raw)
            result = req("GET", "/api/library/progress?book_id=" + corrupt_id)
            record("invalid saved state must not read as valid: " + json.dumps(variant),
                   result == "" and rp.read_bytes() == raw, result)
    finally:
        rp.write_bytes(original_state)

    # A negative schema control with the same valid record except integer metadata.
    lp = DATA / "library.json"
    snapshots = {path: path.read_bytes() if path.is_file() else None
                 for path in [lp, DATA / "library.json.bak", DATA / "library.json.tmp"]}
    try:
        for field in ["chapter_count", "size", "import_version"]:
            invalid = json.loads(snapshots[lp])
            target = next(book for book in invalid["books"] if book["book_id"] == corrupt_id)
            target[field] = 1.5
            raw = json.dumps(invalid).encode()
            lp.write_bytes(raw)
            source = WORK / ("fractional-" + field + ".txt")
            source.write_text(uuid.uuid4().hex, encoding="utf-8")
            result = req("POST", "/api/library/import", dict(path=str(source), author="review-r4", force=False))
            changed = lp.read_bytes() != raw
            after = json.loads(lp.read_bytes())
            rewritten = next(book for book in after["books"] if book["book_id"] == corrupt_id)[field]
            record("fractional " + field + " must reject before index mutation",
                   result.get("code") != "ok" and not changed,
                   dict(outcome=result, index_changed=changed, before=1.5, after=rewritten))
            lp.write_bytes(snapshots[lp])
    finally:
        for path, content in snapshots.items():
            if content is not None:
                path.write_bytes(content)
            elif path.exists():
                path.unlink()

    mixed_lines = ["长" * 4000] + ["短段" + str(index) for index in range(1, 101)]
    mixed_id = import_lines("mixed-paragraph-heights", mixed_lines)
    assert put(mixed_id, state(mixed_id, 50), mixed_lines[50]).get("ok") is True
    print(json.dumps(dict(results=RESULTS, undefined_book_id=undefined_id,
                         corrupt_state_book_id=corrupt_id, mixed_book_id=mixed_id,
                         work=str(WORK)), ensure_ascii=True, indent=2))
    return int(any(result["result"] == "fail" for result in RESULTS))


if __name__ == "__main__":
    raise SystemExit(main())
