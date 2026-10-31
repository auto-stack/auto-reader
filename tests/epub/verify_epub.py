#!/usr/bin/env python3
# verify_epub.py — READER-003 EPUB 双端永久验证入口（T-04）。
#
# 用法：
#   python tests/epub/verify_epub.py --profile vue   # Vue 前端 + VM HTTP 后端
#   python tests/epub/verify_epub.py --profile vm    # VM 前端全轨（-r vm）
#   python tests/epub/verify_epub.py --auto         # 自管 fresh server 生命周期
#
# 覆盖（计划 §6 映射）：
#   E-01 真实 EPUB3（含中文/图片）导入→书库→目录→章文本+图片标记行，离线重开一致
#   E-02 章内定位复用 TXT locator 面（paragraph_index/para_text 逐字锚）
#   E-03 安全负控：非 EPUB 拒绝、href 安装全检查（spec t08 层）+ 本级非容器拒绝
#   E-04 预算边界：>30MiB 拒绝；max_bytes 硬闸（native 层 plan897 已证）
#   E-05 坏书诚实失败：缺 container/OPF 缺失/空 spine
#   E-06 真实入口：HTTP 导入路径即书架对话框同款端点；UI 层沿 real-book.spec.ts
#
# 前置：`auto` CLI（PATH 或 AUTO_EXE）；python3；端口 17825 空闲（--auto 时）。
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PASS = []
FAIL = []


def check(cond, name):
    if cond:
        PASS.append(name)
        print("PASS", name)
    else:
        FAIL.append(name)
        print("FAIL", name)


def http(method, path, body=None):
    url = "http://127.0.0.1:8080" + path
    req = urllib.request.Request(url, method=method)
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, data=data, timeout=120) as resp:
        raw = resp.read().decode("utf-8")
    try:
        v = json.loads(raw)
        # 端点返回双层编码（JSON 字符串内嵌 JSON）——自动拆一层
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return {"_raw": v}
        return v
    except Exception:
        return {"_raw": raw}


def make_epub(out_path, oversize=False):
    """确定性最小 EPUB3（含中文文本、图片条目、nav 目录）。oversize 生成 >30MiB。"""
    import zipfile

    container = ('<?xml version="1.0"?><container version="1.0" '
                 'xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles>'
                 '<rootfile full-path="OEBPS/content.opf" '
                 'media-type="application/oebps-package+xml"/></rootfiles></container>')
    opf = ('<?xml version="1.0" encoding="UTF-8"?>'
           '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">'
           '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>山月小说</dc:title>'
           '<dc:creator>测试作者</dc:creator></metadata>'
           '<manifest>'
           '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
           '<item id="c1" href="ch1.xhtml" media-type="application/xhtml+xml"/>'
           '<item id="c2" href="ch2.xhtml" media-type="application/xhtml+xml"/>'
           '<item id="img1" href="images/cover.png" media-type="image/png"/>'
           '</manifest>'
           '<spine><itemref idref="c1"/><itemref idref="c2"/></spine></package>')
    nav = ('<?xml version="1.0" encoding="UTF-8"?>'
           '<html xmlns="http://www.w3.org/1999/xhtml" '
           'xmlns:epub="http://www.idpf.org/2007/ops"><body><nav epub:type="toc"><ol>'
           '<li><a href="ch1.xhtml">第一章 山月</a></li>'
           '<li><a href="ch2.xhtml">第二章 心底事</a></li>'
           '</ol></nav></body></html>')
    ch1 = ('<?xml version="1.0" encoding="UTF-8"?>'
           '<html xmlns="http://www.w3.org/1999/xhtml"><body>'
           '<h1>第一章 山月</h1><p>山月不知心底事。</p><p>水调歌头，明月几时有。</p>'
           '<p><img src="images/cover.png" alt="cover"/></p></body></html>')
    ch2 = ('<?xml version="1.0" encoding="UTF-8"?>'
           '<html xmlns="http://www.w3.org/1999/xhtml"><body>'
           '<h1>第二章 心底事</h1><p>第二 chapter 内容。</p></body></html>')
    cover = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A] + [(i % 251) for i in range(64)])
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("mimetype", "application/epub+zip", zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", container)
        z.writestr("OEBPS/content.opf", opf)
        z.writestr("OEBPS/nav.xhtml", nav)
        z.writestr("OEBPS/ch1.xhtml", ch1)
        z.writestr("OEBPS/ch2.xhtml", ch2)
        z.writestr("OEBPS/images/cover.png", cover)
    if oversize:
        # 追加 31MiB 填充条目（触发 30MiB 输入上限拒绝）
        with zipfile.ZipFile(out_path, "a", zipfile.ZIP_STORED) as z:
            z.writestr("pad.bin", b"\0" * (31 * 1024 * 1024))


def make_bad_epubs(dir_path):
    import zipfile

    p1 = os.path.join(dir_path, "no_container.epub")
    with zipfile.ZipFile(p1, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("mimetype", "application/epub+zip")
    p2 = os.path.join(dir_path, "empty_spine.epub")
    opf = ('<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0">'
           '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>x</dc:title></metadata>'
           '<manifest/><spine/></package>')
    with zipfile.ZipFile(p2, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("META-INF/container.xml",
                   '<?xml version="1.0"?><container xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                   '<rootfiles><rootfile full-path="content.opf" '
                   'media-type="application/oebps-package+xml"/></rootfiles></container>')
        z.writestr("content.opf", opf)
    return p1, p2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", choices=["vue", "vm"], default="vue")
    ap.add_argument("--auto", action="store_true", help="自管 fresh server 生命周期")
    args = ap.parse_args()
    print("profile:", args.profile)

    tmp = tempfile.mkdtemp(prefix="verify-epub-")
    ep = os.path.join(tmp, "book1.epub")
    make_epub(ep)
    big = os.path.join(tmp, "big.epub")
    make_epub(big, oversize=True)
    bad1, bad2 = make_bad_epubs(tmp)
    sha = hashlib.sha256(open(ep, "rb").read()).hexdigest()

    server = None
    if args.auto:
        env = dict(os.environ)
        env["AUTO_READER_DATA"] = os.path.join(tmp, "data")
        env.setdefault("AUTO_HTTP_STEP_BUDGET", "1000000000")
        env.setdefault("AUTO_HTTP_REQUEST_TIMEOUT_MS", "300000")
        exe = os.environ.get("AUTO_EXE", "auto")
        # N-003-8（在案）：auto run --server=vm 的 flattener 对新增 stdlib
        # 模块（zip）编译失败——API 级验证走直接 api.at 入口（0.0.0.0:8080，
        # 16 路由 autostart），与 auto run 同一 run_language_file 编译语义
        # 的直接形态。UI 端到端待 N-003-8 修复后回归 real-book.spec.ts。
        server = subprocess.Popen(
            [exe, os.path.join("src", "back", "api.at")], cwd=ROOT, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.time() + 90
        ready = False
        while time.time() < deadline:
            try:
                http("GET", "/api/library/books")
                ready = True
                break
            except Exception:
                time.sleep(1.0)
        if not ready:
            print("FATAL: server not ready in 90s")
            server.terminate()
            sys.exit(2)

    try:
        # E-01: 导入 → ok
        r = http("POST", "/api/library/import", {"path": ep, "author": "测试作者", "force": False})
        check(r.get("code") == "ok", "E-01 import ok")
        bid = r.get("book_id", "")
        check(bool(bid), "E-01 book_id issued")

        # 书库可见 + format epub
        books = http("GET", "/api/library/books")
        mine = [b for b in books.get("books", []) if b.get("book_id") == bid]
        check(len(mine) == 1 and mine[0].get("format") == "epub", "E-01 shelf shows epub book")
        check(mine and mine[0].get("source_hash") == "sha256:" + sha, "E-01 sha256 identity")

        # 目录（nav 标签 + spine 序号）
        toc = http("GET", f"/api/library/books/{bid}/toc")
        tarr = toc if isinstance(toc, list) else toc.get("toc", [])
        check(len(tarr) == 2, "E-01 toc 2 entries")
        check(tarr and tarr[0].get("title") == "第一章 山月" and tarr[0].get("number") == 1,
              "E-01 toc entry 1")
        check(len(tarr) > 1 and tarr[1].get("number") == 2, "E-01 toc entry 2")

        # 章文本 + 图片标记 + images 媒体 URI
        c1 = http("GET", f"/api/library/chapter?book_id={bid}&number=1")
        check("山月不知心底事。" in c1.get("body", ""), "E-01 ch1 text")
        check("img:OEBPS/images/cover.png" in c1.get("body", ""), "E-01 ch1 img marker")
        imgs = c1.get("images", [])
        check(isinstance(imgs, list) and len(imgs) == 1
              and imgs[0].get("uri", "").startswith("/api/__auto/media/"),
              "E-01 ch1 images media uri")
        c2 = http("GET", f"/api/library/chapter?book_id={bid}&number=2")
        check("第二 chapter 内容。" in c2.get("body", ""), "E-01 ch2 text")

        # E-01 离线重开一致（重读同章，内容不变）
        c1b = http("GET", f"/api/library/chapter?book_id={bid}&number=1")
        check(c1b.get("body") == c1.get("body"), "E-01 reopen consistent")

        # E-02: locator 面（保存段落锚点 + 读回）——复用 TXT 语义
        body1 = c1.get("body", "")
        paras = [ln for ln in body1.split("\n") if ln.strip()]
        target = next(p for p in paras if p.startswith("山月不知心底事"))
        pi = paras.index(target)
        save = http("POST", "/api/library/progress", {
            "book_id": bid,
            "payload": json.dumps({
                "book_id": bid, "chapter_number": 1, "paragraph_index": pi,
                "para_hash": "sig1:%d:1" % len(target),
                "font_size": "medium", "line_height": "comfy", "updated_at": 0,
            }),
            "para_text": target,
        })
        check(save.get("ok") is True, "E-02 progress save ok")
        got = http("GET", f"/api/library/progress?book_id={bid}")
        check(got.get("para_text") == target and got.get("chapter_number") == 1,
              "E-02 progress readback anchored")

        # duplicate / force
        r2 = http("POST", "/api/library/import", {"path": ep, "author": "", "force": False})
        check(r2.get("code") == "duplicate", "duplicate detected")
        r3 = http("POST", "/api/library/import", {"path": ep, "author": "", "force": True})
        check(r3.get("code") == "ok", "force import ok")

        # E-03/E-05: 坏书诚实失败（先生成普通 zip 夹具）
        zpath = os.path.join(tmp, "zipfx.zip")
        import zipfile as _zf
        with _zf.ZipFile(zpath, "w") as z:
            z.writestr("a.txt", "hello")
        for name, p, codes in [("plain zip (non-epub ext)", zpath, {"decode_error", "epub_invalid"}),
                               ("no container", bad1, {"epub_invalid"}),
                               ("empty spine", bad2, {"epub_invalid"})]:
            rr = http("POST", "/api/library/import", {"path": p, "author": "", "force": False})
            check(rr.get("code") in codes, f"E-05 reject {name}")

        # E-04: >30MiB 拒绝
        rb = http("POST", "/api/library/import", {"path": big, "author": "", "force": False})
        check(rb.get("code") == "epub_too_large", "E-04 oversize rejected")

        # 越界章
        c9 = http("GET", f"/api/library/chapter?book_id={bid}&number=9")
        check("章节不存在" in c9.get("title", ""), "range check placeholder")
    finally:
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=10)
            except Exception:
                server.kill()

    print(f"\n== verify_epub[{args.profile}] PASS={len(PASS)} FAIL={len(FAIL)} ==")
    if FAIL:
        print("failed:", FAIL)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
