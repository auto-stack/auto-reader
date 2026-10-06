"""Independent r5 index controls. Use only a disposable reader001-review-* library."""
import importlib.util
import json
import os
from pathlib import Path
import uuid

spec = importlib.util.spec_from_file_location("r4", Path(__file__).with_name("reader001_r4_repro.py"))
r4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r4)


def main():
    bid = r4.import_lines("r5-integer-control", ["normal"])
    lp = r4.DATA / "library.json"
    snapshots = {p: p.read_bytes() if p.is_file() else None for p in
                 [lp, r4.DATA / "library.json.bak", r4.DATA / "library.json.tmp"]}
    results = []
    try:
        for label, field, value in [("unknown integer control", "rating", 4),
                                    ("unknown fraction compatibility", "rating", 4.5),
                                    ("i32 boundary", "size", 2147483648),
                                    ("i64 boundary", "size", 9223372036854775808),
                                    ("unrepresentable integer", "size", 2**80)]:
            original = json.loads(snapshots[lp])
            target = next(b for b in original["books"] if b["book_id"] == bid)
            target[field] = value
            raw = json.dumps(original).encode()
            lp.write_bytes(raw)
            before = r4.req("GET", "/api/library/books")
            if field == "rating":
                valid = isinstance(before, dict) and any(b["book_id"] == bid for b in before.get("books", []))
                evidence = dict(books_readable=valid, index_changed=lp.read_bytes() != raw)
            else:
                source = r4.WORK / (label.replace(" ", "-") + ".txt")
                source.write_text(uuid.uuid4().hex, encoding="utf-8")
                outcome = r4.req("POST", "/api/library/import", dict(path=str(source), author="r5", force=False))
                after = r4.req("GET", "/api/library/books")
                matching = [b for b in after.get("books", []) if b["book_id"] == bid] if isinstance(after, dict) else []
                preserved = bool(matching) and matching[0][field] == value
                unchanged = lp.read_bytes() == raw
                valid = (outcome.get("code") != "ok" and unchanged) or (outcome.get("code") == "ok" and preserved)
                evidence = dict(outcome=outcome, index_changed=not unchanged,
                                expected_value=value, after_target=matching,
                                value_preserved=preserved, after_readable=isinstance(after, dict))
            results.append(dict(case=label, result="pass" if valid else "fail", evidence=evidence))
            lp.write_bytes(snapshots[lp])
    finally:
        for path, content in snapshots.items():
            if content is not None:
                path.write_bytes(content)
            elif path.exists():
                path.unlink()
    print(json.dumps(dict(results=results, work=str(r4.WORK)), ensure_ascii=True, indent=2))
    return int(any(item["result"] == "fail" for item in results))


if __name__ == "__main__":
    raise SystemExit(main())
