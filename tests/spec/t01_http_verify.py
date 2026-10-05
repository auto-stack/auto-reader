#!/usr/bin/env python3
# t01_http_verify.py — READER-001 T-01 应用级 HTTP 验证驱动。
# 前置：app 以 VM 后端在 127.0.0.1:17825 运行，AUTO_READER_DATA 指向隔离目录。
# 用法：python tests/spec/t01_http_verify.py
# 输出：PASS/FAIL 行 + 摘要；任何 FAIL 以退出码 1 结束。
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request

BASE = os.environ.get("T01_BASE", "http://127.0.0.1:17825")
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FIX = os.path.join(REPO, "tests", "fixtures", "library")
FAILS = []


def req(method, path, body=None):
    url = BASE + path
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    r = urllib.request.Request(url, data=data, method=method)
    if data:
        r.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(r, timeout=30) as resp:
        v = json.loads(resp.read().decode("utf-8"))
    # str 返回端点的响应体是 JSON 编码的字符串（双层编码，spec 增量已记录）
    if isinstance(v, str):
        v = json.loads(v)
    return v


def check(cond, name, detail=""):
    if cond:
        print("PASS " + name)
    else:
        FAILS.append(name)
        print("FAIL " + name + (" :: " + str(detail)[:300] if detail else ""))


def imp(path, author="", force=False):
    return req("POST", "/api/library/import", {"path": path, "author": author, "force": force})


def main():
    # AC-01: 两份中文真实文件导入且逐字核对
    p1 = os.path.join(FIX, "xiaoshuo.txt")
    o1 = imp(p1, "tester1")
    check(o1.get("code") == "ok", "import txt ok", o1)
    b1 = o1.get("book_id", "")
    check(bool(b1), "book_id returned", o1)
    books = req("GET", "/api/library/books")
    lst = books.get("books", [])
    check(len(lst) == 1, "one book listed", books)
    r = lst[0] if lst else {}
    check(r.get("title") == "xiaoshuo", "title from stem", r)
    check(r.get("chapter_count") == 3, "txt chapters=3", r)
    check(str(r.get("source_hash", "")).startswith("ph1:"), "hash prefix ph1", r)
    check(r.get("author") == "tester1", "author recorded", r)
    check(r.get("format") == "txt", "format txt", r)
    ch1 = req("GET", f"/api/library/chapter?book_id={b1}&number=1")
    check(ch1.get("title") == "第一章 山月", "ch1 title verbatim", ch1)
    check(ch1.get("body") == "山月不知心底事，水风空落眼前花。", "ch1 body verbatim", ch1)
    ch3 = req("GET", f"/api/library/chapter?book_id={b1}&number=3")
    check(ch3.get("body") == "萝薜不耐冷，烟波愁杀人。", "ch3 body verbatim", ch3)
    toc = req("GET", f"/api/library/books/{b1}/toc")
    check(len(toc) == 3 and toc[0].get("title") == "第一章 山月", "toc 3 entries", toc)

    p2 = os.path.join(FIX, "notes.md")
    o2 = imp(p2, "tester2")
    check(o2.get("code") == "ok", "import md ok", o2)
    b2 = o2.get("book_id", "")
    mrec = req("GET", f"/api/library/books/{b2}")
    check(mrec.get("format") == "md", "md format", mrec)
    check(mrec.get("chapter_count") == 3, "md chapters=3", mrec)
    mch = req("GET", f"/api/library/chapter?book_id={b2}&number=2")
    check(mch.get("title") == "第一节", "md ch2 title", mch)

    # 受管副本存在且与原文逐字一致；用户原文件不动
    managed = r.get("managed_path", "")
    check(bool(managed) and os.path.exists(managed), "managed copy exists", managed)
    check(open(managed, "rb").read() == open(p1, "rb").read(), "managed copy byte-identical")
    check(os.path.exists(p1), "original untouched after import")

    # AC-03: 同 hash 重复导入明确提示；force 独立档案
    d1 = imp(p1, "", False)
    check(d1.get("code") == "duplicate", "duplicate detected", d1)
    check(d1.get("existing_id") == b1, "duplicate existing_id", d1)
    f1 = imp(p1, "", True)
    check(f1.get("code") == "ok" and f1.get("book_id") != b1, "force distinct archive", f1)

    # AC-04: 错误路径族——不给假成功
    check(imp(os.path.join(FIX, "missing.txt")).get("code") == "invalid_path", "missing file")
    check(imp(FIX).get("code") == "is_dir", "directory rejected")
    check(imp(os.path.join(FIX, "empty.txt")).get("code") == "empty_file", "empty file")
    g = imp(os.path.join(FIX, "gbk.txt"))
    check(g.get("code") == "decode_error", "gbk rejected (real bytes)", g)

    # AC-02: 同标题不同原文件不互相覆盖
    p1c = os.path.join(tempfile.gettempdir(), "t01-xiaoshuo-diff.txt")
    with open(p1c, "w", encoding="utf-8", newline="\n") as f:
        f.write("第一章 山月\n不同出版社的版本内容。\n\n第二章 碧云\n另一版本第二章。\n")
    o3 = imp(p1c, "tester3")
    check(o3.get("code") == "ok", "same-name different-content imports", o3)
    b3 = o3.get("book_id", "")
    check(b3 not in (b1, ""), "distinct book_id for distinct file", o3)
    c1a = req("GET", f"/api/library/chapter?book_id={b1}&number=1")
    c1b = req("GET", f"/api/library/chapter?book_id={b3}&number=1")
    check(c1a.get("body") != c1b.get("body"), "two same-title books distinct bodies")

    # plain 无章头 → 单章文件名题名
    op = imp(os.path.join(FIX, "plain.txt"), "")
    check(op.get("code") == "ok", "plain import ok", op)
    pb = op.get("book_id", "")
    pch = req("GET", f"/api/library/chapter?book_id={pb}&number=1")
    check(pch.get("title") == "plain", "plain single chapter titled by stem", pch)

    # AC-05: 移除可恢复；受管副本与原文件保留
    md_managed = req("GET", f"/api/library/books/{b2}").get("managed_path", "")
    rr = req("DELETE", f"/api/library/books/{b2}")
    check(rr.get("ok") is True, "remove ok", rr)
    books2 = req("GET", "/api/library/books")
    check(all(x.get("book_id") != b2 for x in books2.get("books", [])), "removed from shelf")
    check(os.path.exists(md_managed), "managed copy kept after remove")
    check(os.path.exists(p2), "original file kept after remove")
    removed_log = os.path.join(os.environ["AUTO_READER_DATA"], "removed.jsonl")
    check(os.path.exists(removed_log), "removed.jsonl exists")
    rs = req("POST", f"/api/library/books/{b2}/restore")
    check(rs.get("ok") is True, "restore ok", rs)
    mrec2 = req("GET", f"/api/library/books/{b2}")
    check(mrec2.get("title") == "notes", "restored record readable", mrec2)
    mch2 = req("GET", f"/api/library/chapter?book_id={b2}&number=1")
    check(mch2.get("title") == "上卷", "restored chapter verbatim", mch2)

    print(f"--- summary: {len(FAILS)} fails ---")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
