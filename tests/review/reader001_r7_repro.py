"""Independent r7 final-review controls for removed-record restore admission.

New vectors chosen independently of the work-phase regressions (r6 driver,
t06 S13): envelope-level admission (removed_at bounds/types, duplicate keys,
trailing content), record-level keys not exercised by r6 (exponent, null,
missing field, numeric title), the fail-closed multi-line policy (a corrupt
line for book A must block restoring book B), HTTP i32-minimum losslessness
and repeated-restore idempotency/error. Lines are rebuilt from parsed dicts
with compact separators so tampering cannot silently no-op.
Only operate on an existing disposable reader001-review-* VM library.
"""
import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location("r4", Path(__file__).with_name("reader001_r4_repro.py"))
r4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r4)

TRACKED = ["library.json", "library.json.bak", "library.json.tmp", "removed.jsonl"]


def cdumps(obj):
    return json.dumps(obj, separators=(",", ":"))


def snapshots():
    return {p: p.read_bytes() if p.is_file() else None for p in [r4.DATA / n for n in TRACKED]}


def restore(saved):
    for path, content in saved.items():
        if content is not None:
            path.write_bytes(content)
        elif path.exists():
            path.unlink()


def unchanged(saved):
    return all((p.read_bytes() if p.is_file() else None) == c for p, c in saved.items())


def main():
    results = []
    bid_a = r4.import_lines("r7-final-book-a", ["alpha body"])
    bid_b = r4.import_lines("r7-final-book-b", ["bravo body"])
    bid_c = r4.import_lines("r7-final-book-c", ["charlie body"])
    lp = r4.DATA / "library.json"
    rp = r4.DATA / "removed.jsonl"

    def check(name, ok, **evidence):
        results.append(dict(case=name, result="pass" if ok else "fail", evidence=evidence))

    # Real removals: A and B removed, C stays live; each case rewrites the
    # two-line log from its own untrusted copy.
    assert r4.req("DELETE", "/api/library/books/" + bid_a).get("ok") is True
    assert r4.req("DELETE", "/api/library/books/" + bid_b).get("ok") is True
    pristine = snapshots()
    entries = {json.loads(e)["book_id"]: json.loads(e)
               for e in (pristine[rp] or b"").decode().splitlines() if e.strip()}
    rec_a, rec_b = entries[bid_a], entries[bid_b]
    assert bid_c not in entries
    size_a = rec_a["record"]["size"]

    def with_record(base, mutate):
        entry = json.loads(json.dumps(base))
        mutate(entry)
        return cdumps(entry)

    # V-1..V-8: envelope/record admission on the selected entry (book B).
    tamper = [
        ("envelope removed_at overflow", with_record(rec_b, lambda e: e.update(removed_at=2147483648))),
        ("envelope removed_at string", with_record(rec_b, lambda e: e.update(removed_at="0"))),
        ("envelope duplicate book_id", cdumps(rec_b)[:-1] + ',"book_id":"' + bid_b + '"}'),
        ("record chapter_count exponent", with_record(rec_b, lambda e: None)
            .replace('"chapter_count":1,', '"chapter_count":1e2,')),
        ("record import_version null", with_record(rec_b, lambda e: e["record"].update(import_version=None))),
        ("record missing managed_path", with_record(rec_b, lambda e: e["record"].pop("managed_path"))),
        ("record title numeric", with_record(rec_b, lambda e: e["record"].update(title=5))),
        ("trailing content", cdumps(rec_b) + " tail"),
    ]
    for name, line in tamper:
        log = cdumps(rec_a) + "\n" + line + "\n"
        rp.write_bytes(log.encode())
        before = snapshots()
        outcome = r4.req("POST", "/api/library/books/" + bid_b + "/restore")
        ok = outcome.get("ok") is False and unchanged(before)
        check(name + " -> reject, bytes unchanged", ok,
              outcome=outcome, files_unchanged=unchanged(before), line=line[:80])
        restore(pristine)

    # V-9: fail-closed multi-line policy — corrupt line for A must block B.
    bad_a = with_record(rec_a, lambda e: e["record"].update(size=1.5))
    rp.write_bytes((bad_a + "\n" + cdumps(rec_b) + "\n").encode())
    before = snapshots()
    outcome = r4.req("POST", "/api/library/books/" + bid_b + "/restore")
    check("corrupt sibling line blocks restore (fail-closed)",
          outcome.get("ok") is False and unchanged(before),
          outcome=outcome, files_unchanged=unchanged(before))
    restore(pristine)

    # V-10: valid log, both lines — restore B, A line must survive verbatim.
    rp.write_bytes((cdumps(rec_a) + "\n" + cdumps(rec_b) + "\n").encode())
    before = snapshots()
    outcome = r4.req("POST", "/api/library/books/" + bid_b + "/restore")
    disk = json.loads(lp.read_bytes())
    match = [b for b in disk["books"] if b["book_id"] == bid_b]
    kept = [e for e in (rp.read_bytes() or b"").decode().splitlines() if e.strip()]
    ok = (outcome.get("ok") is True and bool(match)
          and match[0]["size"] == rec_b["record"]["size"] and kept == [cdumps(rec_a)])
    check("valid restore succeeds, sibling line verbatim", ok,
          outcome=outcome, restored_size=match[0]["size"] if match else None,
          kept_lines=len(kept))
    restore(pristine)

    # V-11: i32 minimum lossless over HTTP.
    a_min = with_record(rec_a, lambda e: e["record"].update(size=-2147483648))
    rp.write_bytes((a_min + "\n" + cdumps(rec_b) + "\n").encode())
    outcome = r4.req("POST", "/api/library/books/" + bid_a + "/restore")
    disk = json.loads(lp.read_bytes())
    match = [b for b in disk["books"] if b["book_id"] == bid_a]
    got = r4.req("GET", "/api/library/books")
    ok = (outcome.get("ok") is True and bool(match) and match[0]["size"] == -2147483648
          and isinstance(got, dict))
    check("i32 minimum restored lossless, library readable", ok,
          outcome=outcome, size=match[0]["size"] if match else None)
    restore(pristine)

    # V-12: unknown keys at both levels stay compatible.
    b_unk = with_record(rec_b, lambda e: (e["record"].update(rating=4.5), e.update(note={"k": [1, 2]})))
    rp.write_bytes((cdumps(rec_a) + "\n" + b_unk + "\n").encode())
    outcome = r4.req("POST", "/api/library/books/" + bid_b + "/restore")
    disk = json.loads(lp.read_bytes())
    match = [b for b in disk["books"] if b["book_id"] == bid_b]
    check("unknown legal keys restore ok", outcome.get("ok") is True and bool(match),
          outcome=outcome)
    restore(pristine)

    # V-13: unknown book -> explicit error, bytes unchanged.
    before = snapshots()
    outcome = r4.req("POST", "/api/library/books/" + bid_c + "/restore")
    check("unknown book explicit error, bytes unchanged",
          outcome.get("ok") is False and unchanged(before), outcome=outcome,
          files_unchanged=unchanged(before))
    restore(pristine)

    # V-14: repeated restore — second attempt explicit error, bytes unchanged.
    rp.write_bytes((cdumps(rec_a) + "\n" + cdumps(rec_b) + "\n").encode())
    first = r4.req("POST", "/api/library/books/" + bid_b + "/restore")
    mid = snapshots()
    second = r4.req("POST", "/api/library/books/" + bid_b + "/restore")
    check("second restore explicit error, bytes unchanged",
          first.get("ok") is True and second.get("ok") is False and unchanged(mid),
          second=second, files_unchanged=unchanged(mid))
    restore(pristine)

    restore(pristine)
    print(json.dumps(dict(results=results, book_a=bid_a, book_b=bid_b, book_c=bid_c,
                          control_size_a=size_a),
                     ensure_ascii=True, indent=2))
    return int(any(r["result"] == "fail" for r in results))


if __name__ == "__main__":
    raise SystemExit(main())
