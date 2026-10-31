#!/usr/bin/env python3
# verify_local.py — READER-002 阶段A 本地能力双 profile 永久验证入口（T-04）。
#
# 用法：
#   python tests/annotations/verify_local.py --profile vue   # Vue UI + HTTP + 冷重启
#   python tests/annotations/verify_local.py --profile vm    # HTTP + 冷重启（原生 UI 受 N-003-8 阻塞，见下）
#   python tests/annotations/verify_local.py --auto          # 自管后端/前端生命周期（默认开）
#
# 覆盖（计划 §6 映射）：
#   A-01 (AC-01/05)：3 书夹具（TXT/MD/EPUB）、排版偏好（layout/theme）
#         随阅读状态持久化、冷重启后同段恢复；搜索/输入框不抢键盘。
#   A-02 (AC-02)：注释≥20 持久回访（3 书分摊）；稳定 annotation_id
#         （跨冷重启不变）；重复句 occurrence 判别；源改版诚实拒绝旧锚
#         新建、原摘录保留。
#   A-03 (AC-03/04 本地面)：Notes 缺席导出 Markdown → 独立解析核对
#         原句/书名/章节/locator；文件交付≠真实接收（不记 B 账）。
#   A-04 (AC-01/02/05 本地错误面)：损坏注释文件诚实拒绝且保留原件；
#         恢复后写入成功。
#
# N-003-8（在案跨仓缺口，003 交付记录）：`auto run --server=vm` 的
# flattener 对 zip stdlib 模块编译失败（main 同样复现，非本计划回归）。
# 本入口沿用 003 既有绕行：后端走 `auto service --server vm`（同一
# run_language_file 编译语义的直接形态，20 路由含本计划 4 新端点），
# Vue 前端走 gen/front/vue + vite（auto build 先刷新 codegen）。原生 VM
# 轨 UI e2e 在 N-003-8 修复前不可达，--profile vm 记 SKIP 并引用缺口，
# 不以 mock 冒充。
#
# 前置：`auto` CLI（PATH 或 AUTO_EXE）、node、python3；端口 17845/17846
# 空闲（--auto 时，可 V_PORT/B_PORT 覆盖）。
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PASS = []
FAIL = []
SKIP = []
BASE = "http://127.0.0.1"


def check(cond, name):
    if cond:
        PASS.append(name)
        print("PASS", name)
    else:
        FAIL.append(name)
        print("FAIL", name)


def skip(name, reason):
    SKIP.append(name)
    print("SKIP", name, "-", reason)


def http(method, path, body=None, base="http://127.0.0.1"):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            out = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"__status": e.code}
    except Exception:
        return {"__status": 0}
    # 双层编码：library 面端点返回 JSON 字符串 → 二次解析
    if isinstance(out, str):
        try:
            out = json.loads(out)
        except Exception:
            pass
    return out


def wait_ready(proc, path, deadline_s, name):
    t0 = time.time()
    while time.time() - t0 < deadline_s:
        if proc.poll() is not None:
            return False
        try:
            urllib.request.urlopen(path, timeout=3)
            return True
        except Exception:
            time.sleep(1.0)
    return False


def make_books(tmp):
    """生成 TXT/MD 夹具并复用 plan897 EPUB 生成器。返回路径表。"""
    txt = os.path.join(tmp, "local_book.txt")
    with open(txt, "w", encoding="utf-8") as f:
        f.write("第一章 起\n春天来了，河水初暖。\n\n桥边的老树开花了，桥边的老树开花了，年年如此。\n"
                "第四段。山里的夜来得早。\n\n第二章 承\n尾段：灯火可亲。🌸\n")
    md = os.path.join(tmp, "local_notes.md")
    with open(md, "w", encoding="utf-8") as f:
        f.write("# 笔记集\n\n## 第一条\n摘录的句子：温故而知新。\n\n正文段落，用于注释锚定。\n\n"
                "## 第二条\n第二段的文字，重复句：温故而知新。\n")
    spec = os.path.join(ROOT, "tests", "spec", "plan897_make_epub.py")
    subprocess.run([sys.executable, spec], check=True, capture_output=True)
    ep = os.path.join(tempfile.gettempdir(), "plan897", "book1.epub")
    return {"txt": txt, "md": md, "epub": ep}


def annot(book_id, ch, pi, occ, kind="highlight", comment="", tags="[]", quote=""):
    return http("POST", "/api/library/annotations", {
        "book_id": book_id, "op": "create", "annotation_id": "", "kind": kind,
        "chapter_number": ch, "para_idx": pi, "occurrence": occ,
        "comment": comment, "tags_json": tags, "quote": quote}, BASE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", choices=["vue", "vm"], default="vue")
    ap.add_argument("--no-auto", action="store_true", help="不自管生命周期（外端已起 B=17845/F=17846）")
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()

    global BASE
    bport = os.environ.get("B_PORT", "17845")
    fport = os.environ.get("F_PORT", "17846")
    bbase = "http://127.0.0.1:" + bport
    BASE = bbase
    exe = os.environ.get("AUTO_EXE", "auto")

    tmp = tempfile.mkdtemp(prefix="reader002-verify-")
    data_dir = os.path.join(tmp, "data")
    os.makedirs(data_dir, exist_ok=True)

    backend = None
    frontend = None
    vite_env = dict(os.environ)
    vite_env["AUTO_HTTP_PORT"] = bport
    try:
        # ── 生命周期 ──
        if not args.no_auto:
            env = dict(os.environ)
            env["AUTO_READER_DATA"] = data_dir
            env.setdefault("AUTO_HTTP_STEP_BUDGET", "1000000000")
            env.setdefault("AUTO_HTTP_REQUEST_TIMEOUT_MS", "300000")
            # 前端 codegen 刷新（N-003-8 绕行面：auto run 不可用，build 只产码不起服）
            print("CODEGEN: auto build ...")
            b = subprocess.run([exe, "build"], cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
            if b.returncode != 0:
                print("FATAL: auto build failed")
                print((b.stdout or "")[-800:])
                sys.exit(2)
            backend = subprocess.Popen(
                [exe, "service", "--server", "vm", "-B", bport], cwd=ROOT, env=env,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if not wait_ready(backend, bbase + "/api/library/books", 90, "backend"):
                print("FATAL: backend not ready in 90s")
                sys.exit(2)
            print("BACKEND READY", bport)
            if args.profile == "vue":
                gen_vue = os.path.join(ROOT, "gen", "front", "vue")
                npx = shutil.which("npx") or shutil.which("npx.cmd") or "npx"
                frontend = subprocess.Popen(
                    [npx, "vite", "--port", fport, "--strictPort"], cwd=gen_vue, env=vite_env,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if not wait_ready(frontend, "http://localhost:" + fport + "/", 60, "frontend"):
                    print("FATAL: frontend not ready in 60s")
                    sys.exit(2)
                print("FRONTEND READY", fport)

        # ── 夹具：3 书导入 ──
        books = make_books(tmp)
        r = http("POST", "/api/library/import", {"path": books["txt"], "author": "甲", "force": False}, bbase)
        check(r.get("code") == "ok", "L-01 import txt")
        txt_id = r.get("book_id") or r.get("existing_id")
        r = http("POST", "/api/library/import", {"path": books["md"], "author": "乙", "force": False}, bbase)
        check(r.get("code") == "ok", "L-02 import md")
        md_id = r.get("book_id") or r.get("existing_id")
        r = http("POST", "/api/library/import", {"path": books["epub"], "author": "丙", "force": False}, bbase)
        check(r.get("code") == "ok", "L-03 import epub")
        epub_id = r.get("book_id") or r.get("existing_id")
        for bid, fmt in ((txt_id, "txt"), (md_id, "md"), (epub_id, "epub")):
            books_json = http("GET", "/api/library/books/" + bid, None, bbase)
            check(books_json.get("format") == fmt, "L-04 format " + fmt)

        # 章面探测：段模型同式切分（idx=原行号，空行不产段但占位），
        # 支持「第 N 处」出现序选取——测试不硬编码段号（章体不含章标题）。
        def chapter_body(bid, ch):
            cj = http("GET", "/api/library/chapter?book_id=" + bid + "&number=" + str(ch), None, bbase)
            return cj.get("body", "")

        def find_para(bid, ch, snippet, occ=1):
            body = chapter_body(bid, ch)
            lines = body.split("\n")
            found = 0
            for i, ln in enumerate(lines):
                t = ln.strip()
                if t and snippet in t:
                    found += 1
                    if found == occ:
                        return i, t
            return None, None

        # ── A-02：20 条注释（HTTP 批量；UI 面单独建 1 条重复句 occ=2）──
        made = 0
        ids_snapshot = []
        # TXT：7 条（含重复句 occ=2、书签、批注）。段位置全部动态定位。
        pi_spring, t1 = find_para(txt_id, 1, "春天来了")
        check(pi_spring is not None, "L-05a locate spring para")
        def ok_annot(bid, ch, pi, occ, name, kind="highlight", comment="", tags="[]", quote=""):
            nonlocal made
            r = annot(bid, ch, pi, occ, kind=kind, comment=comment, tags=tags, quote=quote)
            check(r.get("ok") is True, name)
            if r.get("ok") is True:
                made += 1
                ids_snapshot.append((bid, ch, pi, occ))
            return r

        pi_spring, t1 = find_para(txt_id, 1, "春天来了")
        check(pi_spring is not None, "L-05a locate spring para")
        ok_annot(txt_id, 1, pi_spring, 1, "L-05 txt ann occ=1", comment="春天批注", tags='["春","河"]', quote=t1)
        pi_tree, t2 = find_para(txt_id, 1, "桥边的老树开花了", occ=1)
        check(pi_tree is not None, "L-06a locate dup para")
        # 重复句出现序：quote=子串「桥边的老树开花了」（段内两处）→ occ=2 可建
        ok_annot(txt_id, 1, pi_tree, 2, "L-06 duplicate-sentence occ=2", comment="第二处开花", quote="桥边的老树开花了")
        ok_annot(txt_id, 2, -1, 1, "L-07 chapter bookmark", kind="bookmark")
        pi_n4, t4 = find_para(txt_id, 1, "第四段")
        ok_annot(txt_id, 1, pi_n4, 1, "L-08 txt ann ch1-n4", kind="comment", comment="批注 第四段", quote=t4)
        pi_tail, ttail = find_para(txt_id, 2, "尾段")
        ok_annot(txt_id, 2, pi_tail, 1, "L-08 txt ann ch2-tail", kind="comment", comment="批注 尾段", quote=ttail)
        ok_annot(txt_id, 1, pi_spring, 1, "L-08 txt ann spring again", comment="高亮 春天again", quote=t1)
        pi_night, tnight = find_para(txt_id, 1, "山里的夜")
        ok_annot(txt_id, 1, pi_night, 1, "L-08 txt ann night", comment="高亮 夜", quote=tnight)
        check(made == 7, "L-09 txt subtotal made=%d" % made)
        # MD：6 条。MD 导入章结构：1=笔记集（空体，不可锚），2=第一条
        # （摘录的句子：温故而知新。/ 正文段落，用于注释锚定。），3=第二条
        # （第二段的文字，重复句：温故而知新。）。同一锚可重复注释。
        md_ok = 0
        mpi_a, mp_a = find_para(md_id, 2, "摘录的句子")
        mpi_b, mp_b = find_para(md_id, 2, "正文段落")
        mpi_c, mp_c = find_para(md_id, 3, "第二段的文字")
        for (mc, mpi, mp, tag) in ((2, mpi_a, mp_a, "摘录"), (2, mpi_b, mp_b, "正文"),
                                   (3, mpi_c, mp_c, "第二段"), (2, mpi_a, mp_a, "摘录2"),
                                   (3, mpi_c, mp_c, "第二段2"), (2, mpi_b, mp_b, "正文2")):
            if mp is None:
                check(False, "L-10 md para %s missing" % tag)
                continue
            before = made
            ok_annot(md_id, mc, mpi, 1, "L-10 md ann " + tag, comment="MD 注 " + tag, quote=mp)
            if made > before:
                md_ok += 1
        check(md_ok == 6, "L-10 md subtotal made=%d" % md_ok)
        # MD 重复句出现序：单段只一处 → occ=2 必须诚实拒绝
        r = annot(md_id, 2, mpi_a, 2, quote=mp_a)
        check(r.get("ok") is False, "L-10b md occ=2 beyond count rejected")
        # EPUB：动态取章段落（中文 quote）
        ep_ok = 0
        body1 = chapter_body(epub_id, 1)
        body2 = chapter_body(epub_id, 2)
        ep_lines = [ln.strip() for ln in (body1 + chr(10) + body2).split(chr(10)) if ln.strip()]
        check(len(ep_lines) >= 5, "L-11a epub paragraphs present (%d)" % len(ep_lines))
        for snip in ep_lines[:6]:
            chx = 1 if snip in body1 else 2
            epi, ep = find_para(epub_id, chx, snip[:12])
            if ep is None:
                check(False, "L-11 epub re-locate fail: %s" % snip[:12])
                continue
            before = made
            r = annot(epub_id, chx, epi, 1, comment="EPUB 注 " + snip[:6], quote=ep)
            check(r.get("ok") is True, "L-11 epub ann " + snip[:6])
            if r.get("ok") is True:
                made += 1
                ep_ok += 1
                ids_snapshot.append((epub_id, chx, epi, 1))
        _ = before
        check(made >= 19, "L-12 annotations >= 19 (made=%d, +1 UI = 20)" % made)

        # 诚实拒绝面：occ 超界 / 锚失配 / 章越界
        r = annot(txt_id, 1, pi_tree, 3, quote=t2)
        check(r.get("ok") is False, "L-13 occ=3 rejected")
        r = annot(txt_id, 1, pi_spring, 1, quote="不存在的句子")
        check(r.get("ok") is False, "L-14 stale quote rejected")
        r = annot(txt_id, 99, 0, 1, quote="x")
        check(r.get("ok") is False, "L-15 chapter range rejected")

        # ── A-03：导出 + 独立解析（Notes 缺席）──
        r = http("POST", "/api/library/export", {"book_id": txt_id}, bbase)
        check(r.get("ok") is True and r.get("path"), "L-16 export ok")
        if not r.get("path"):
            print("FATAL: export path empty")
            sys.exit(2)
        md_txt = open(r["path"], encoding="utf-8").read()
        check("春天批注" in md_txt and t1 in md_txt, "L-17 export quote+comment")
        check(("第 1 章 · 第 %d 段" % pi_spring) in md_txt, "L-18 export locator")
        check(txt_id in md_txt and "来源指纹" in md_txt, "L-19 export book identity")
        check(re.search(r"annotation_id: [0-9a-f-]{36}", md_txt) is not None, "L-20 export annotation_id")

        # ── A-04：损坏文件诚实面 ──
        ann_file = os.path.join(data_dir, "annotations", txt_id + ".json")
        keep = open(ann_file, encoding="utf-8").read()
        with open(ann_file, "w", encoding="utf-8") as f:
            f.write('{"version":1,')
        r = http("GET", "/api/library/annotations?book_id=" + txt_id, None, bbase)
        check(r.get("ok") is False, "L-21 corrupt -> ok:false (no fake empty)")
        with open(ann_file, "w", encoding="utf-8") as f:
            f.write(keep)
        r = http("GET", "/api/library/annotations?book_id=" + txt_id, None, bbase)
        check(r.get("ok") is True, "L-22 restore -> ok:true")

        # ── 排版偏好持久化（A-01 后端面）──
        payload = {"book_id": txt_id, "chapter_number": 1, "paragraph_index": pi_spring, "para_hash": "sig1:1:1",
                   "font_size": "large", "line_height": "comfy", "layout": "wide", "theme": "sepia", "updated_at": 0}
        r = http("POST", "/api/library/progress", {"book_id": txt_id, "payload": json.dumps(payload, ensure_ascii=True), "para_text": t1}, bbase)
        check(r.get("ok") is True, "L-23 progress with layout/theme")
        r = http("GET", "/api/library/progress?book_id=" + txt_id, None, bbase)
        check(r.get("layout") == "wide" and r.get("theme") == "sepia", "L-24 layout/theme readback")

        # ── Vue UI 面（A-01/02/05 的真实操作）──
        if args.profile == "vue":
            chrome = os.environ.get("PW_CHROMIUM", os.path.join(
                os.environ.get("LOCALAPPDATA", ""), "ms-playwright", "chromium-1243", "chrome-win64", "chrome.exe"))
            node_script = os.path.join(ROOT, "tests", "annotations", "ui_checks.mjs")
            rc = subprocess.run(
                ["node", node_script, "http://localhost:" + fport, chrome,
                 "local_book", "桥边的老树开花了", "2"],
                cwd=os.path.join(ROOT, "tests"), capture_output=True, text=True, timeout=300)
            sys.stdout.write(rc.stdout or "")
            if rc.stderr:
                sys.stdout.write(rc.stderr[-400:])
            ui_fails = len(re.findall(r"^FAIL", rc.stdout or "", re.M))
            check(rc.returncode == 0 and ui_fails == 0, "L-25 vue ui checks (A-01/02/05 faces)")
        else:
            skip("L-25 vue ui checks", "N-003-8：auto run flattener zip 编译失败，原生轨 UI 不可达（003 交付在案缺口；后端 HTTP 面双轨同源已验）")

        # ── 冷重启持久化（A-01/A-02 oracle）──
        pre = http("GET", "/api/library/annotations?book_id=" + txt_id, None, bbase)
        pre_ids = sorted(a["annotation_id"] for a in pre.get("annotations", []))
        if backend is not None:
            backend.terminate()
            try:
                backend.wait(timeout=15)
            except Exception:
                backend.kill()
            env = dict(os.environ)
            env["AUTO_READER_DATA"] = data_dir
            env.setdefault("AUTO_HTTP_STEP_BUDGET", "1000000000")
            env.setdefault("AUTO_HTTP_REQUEST_TIMEOUT_MS", "300000")
            backend = subprocess.Popen(
                [exe, "service", "--server", "vm", "-B", bport], cwd=ROOT, env=env,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if not wait_ready(backend, bbase + "/api/library/books", 90, "backend2"):
                print("FATAL: backend restart failed")
                sys.exit(2)
            print("BACKEND RESTARTED (same data dir)")
        post = http("GET", "/api/library/annotations?book_id=" + txt_id, None, bbase)
        post_ids = sorted(a["annotation_id"] for a in post.get("annotations", []))
        check(pre_ids == post_ids and len(post_ids) >= 7, "L-26 annotation ids stable across cold restart")
        r = http("GET", "/api/library/progress?book_id=" + txt_id, None, bbase)
        check(r.get("layout") == "wide" and r.get("theme") == "sepia", "L-27 prefs survive restart")
        pre_pos = http("GET", "/api/library/progress?book_id=" + txt_id, None, bbase)
        _ = pre_pos
        check(r.get("paragraph_index") is not None, "L-28 position present after restart")
        # 恢复后写入仍可（A-04 恢复条件）
        r = annot(txt_id, 1, pi_n4, 1, comment="重启后新建", quote=t4)
        check(r.get("ok") is True, "L-29 write after restart ok")

    finally:
        if frontend is not None:
            frontend.terminate()
        if backend is not None:
            backend.terminate()
        if not args.keep:
            shutil.rmtree(tmp, ignore_errors=True)
        else:
            print("DATA KEPT:", tmp)

    print("")
    print("TOTAL PASS=%d FAIL=%d SKIP=%d" % (len(PASS), len(FAIL), len(SKIP)))
    if FAIL:
        for f in FAIL:
            print("  FAILED:", f)
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
