"""Independent r6 controls for index admission and removed-record restoration.

Only operate on an existing disposable reader001-review-* VM library.
"""
import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location("r4", Path(__file__).with_name("reader001_r4_repro.py"))
r4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r4)


def snapshots():
    return {p: p.read_bytes() if p.is_file() else None for p in
            [r4.DATA / name for name in ["library.json", "library.json.bak", "library.json.tmp", "removed.jsonl"]]}


def reset(saved):
    for path, content in saved.items():
        if content is not None:
            path.write_bytes(content)
        elif path.exists():
            path.unlink()


def unchanged(saved):
    return all((p.read_bytes() if p.is_file() else None) == content for p, content in saved.items())


def main():
    results = []
    bid = r4.import_lines("r6-restore-control", ["normal", "second"])
    lp = r4.DATA / "library.json"
    initial = snapshots()
    try:
        for key in ["size", "chapter_count", "import_version", "created_at"]:
            for value in [2147483647, -2147483648, 2147483648, -2147483649]:
                obj = json.loads(initial[lp])
                next(b for b in obj["books"] if b["book_id"] == bid)[key] = value
                raw = json.dumps(obj).encode()
                lp.write_bytes(raw)
                got = r4.req("GET", "/api/library/books")
                legal = -(2**31) <= value < 2**31
                match = [b for b in got.get("books", []) if b["book_id"] == bid] if isinstance(got, dict) else []
                ok = bool(match) and match[0][key] == value if legal else got == ""
                results.append(dict(case=f"index {key}={value}", result="pass" if ok else "fail",
                                    evidence=dict(readable=isinstance(got, dict), unchanged=lp.read_bytes() == raw)))
                reset(initial)
        for value in [4.5, 100.0, {"extra": 1}, [1, 2]]:
            obj = json.loads(initial[lp])
            next(b for b in obj["books"] if b["book_id"] == bid)["rating"] = value
            raw = json.dumps(obj)
            # Exercise an actual exponent token, not Python's decimal 100.0.
            label = json.dumps(value)
            if value == 100.0:
                raw = raw.replace('"rating": 100.0', '"rating": 1e2')
                label = "1e2"
            lp.write_bytes(raw.encode())
            got = r4.req("GET", "/api/library/books")
            ok = isinstance(got, dict) and any(b["book_id"] == bid for b in got.get("books", []))
            results.append(dict(case="unknown record value " + label, result="pass" if ok else "fail"))
            reset(initial)

        assert r4.req("DELETE", "/api/library/books/" + bid).get("ok") is True
        removed = snapshots()
        rp = r4.DATA / "removed.jsonl"
        entries = [json.loads(line) for line in removed[rp].splitlines() if line.strip()]
        for label, value, legal in [("valid removed record", None, True),
                                    ("removed record i32 maximum", 2147483647, True),
                                    ("removed record overflow", 2147483648, False),
                                    ("removed record fraction", 1.5, False)]:
            entries_copy = json.loads(json.dumps(entries))
            if value is not None:
                next(e for e in entries_copy if e["book_id"] == bid)["record"]["size"] = value
            rp.write_bytes(("\n".join(json.dumps(e) for e in entries_copy) + "\n").encode())
            before = snapshots()
            outcome = r4.req("POST", "/api/library/books/" + bid + "/restore", {})
            disk = json.loads(lp.read_bytes())
            match = [b for b in disk["books"] if b["book_id"] == bid]
            old_record = next(e for e in entries_copy if e["book_id"] == bid)["record"]
            got = r4.req("GET", "/api/library/books")
            ok = (outcome.get("ok") is True and bool(match) and match[0]["size"] == old_record["size"]
                  and isinstance(got, dict)) if legal else (outcome.get("ok") is False and unchanged(before))
            results.append(dict(case=label, result="pass" if ok else "fail",
                                evidence=dict(outcome=outcome, files_unchanged=unchanged(before),
                                              before_size=old_record["size"], after_size=match[0]["size"] if match else None,
                                              library_readable=isinstance(got, dict))))
            reset(removed)
    finally:
        reset(initial)
    print(json.dumps(dict(results=results, book_id=bid), ensure_ascii=True, indent=2))
    return int(any(item["result"] == "fail" for item in results))


if __name__ == "__main__":
    raise SystemExit(main())
