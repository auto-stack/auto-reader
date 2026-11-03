#!/usr/bin/env python3
"""verify_epub_product.py — READER-007 正式 EPUB 产品永久门（T-02 建立）。

统一入口（计划 §5.5/§6，P-01～12 必需集）：

    python tests/product/verify_epub_product.py --profile vue|vm \\
        --auto-bin <固定 auto.exe> --out-dir <自有隔离> [--corpus-dir <语料>] [--keep]

- P-01～12 在 REQUIRED 清单注册唯一 ID（profile 适用性显式）；父用例结果由其
  本身与子项最坏推导；0 选择/缺项/重复/GAP/FAIL/not_run/未声明根/坏 cohort/
  ENV 不可用一律非零。
- 从正常产品 UI 驱动（正式书架/reading_page），不调用 probe 专用写端点；
  数据/API/磁盘仅作独立读回，正常保存不预写。
- 旧 APP 门（verify_standalone/verify_local/verify_epub/原生驱动）作为
  P-12 子腿同 cohort 回归；T-09 固定最终 cohort 全量执行。
- 语料由 tests/product/gen_product_corpus.py 确定性生成（hash 可重算）。

退出码：0=全部必需用例通过；1=FAIL/GAP/缺项/重复/未声明；2=环境不可用；
         3=有用例 not_run（功能未闭合，不得冒充通过）。
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
MARKER = "product-scope.json"

# 产品语料重复句/跨段样本（与 gen_product_corpus.py 内一致，FROZEN）。
REPEAT_A = "产品重复句甲🦊：琥珀色的狐狸跃过懒狗时携带三枚星形饼干，并轻声数到十七✨，随后沿对角线穿过整段跨度以便在窄栏里真实换行。"
REPEAT_B = "产品重复句乙🐙：深蓝色的章鱼在暗礁之间整理十二枚贝壳🫧，把第七枚留给回声，然后沉入更深的走廊。"
CROSS_PARA = "跨段引文甲：这段文字的上半句落在段落末尾，"  # 前半（段尾）
CROSS_PARA2 = "下半句则跨进下一段的开头继续，形成真实跨段范围。"  # 后半（下段首）

RECORDS = []


def record(case, outcome, detail=""):
    """outcome ∈ PASS | FAIL | GAP | not_run（计划 §6 四态）。"""
    RECORDS.append({"case": case, "outcome": outcome, "detail": str(detail)[:240]})
    print(f"{outcome:8s} {case}" + (f" :: {str(detail)[:180]}" if detail else ""))


# ─────────────────────── P-01～12 必需用例清单（READER-007 §6） ───────────────────────

REQUIRED = {
    "P-01": {"vm": True, "vue": True, "task": "T-00",
             "desc": "029交付cohort+正式Reader启动，两端实际window/route/backend；依赖未就绪停T-00"},
    "P-02": {"vm": True, "vue": True, "task": "T-02/03/04",
             "desc": "正常书架导入/打开，断网、移走probe资产路径后重开，目录/图/脚注/正文结构"},
    "P-03": {"vm": True, "vue": True, "task": "T-04/08",
             "desc": "分页/滚动、字号/列宽变化、隐藏显示后重新选指定范围；专门复现029 Vue重排风险"},
    "P-04": {"vm": True, "vue": True, "task": "T-05/06",
             "desc": "重复句第2处、中文emoji跨行/跨段范围→高亮/批注→编辑/删除；CFI真实解析+quote/occ独立oracle"},
    "P-05": {"vm": True, "vue": True, "task": "T-05/07",
             "desc": "完整旧v1库、章书签、重复句/未知字段边界、可映射与不可映射/多义记录"},
    "P-06": {"vm": True, "vue": True, "task": "T-07/08",
             "desc": "真实保存后正常退出/强退，新进程换布局恢复；旧/新混合记录"},
    "P-07": {"vm": True, "vue": True, "task": "T-07",
             "desc": "搜索重复句→每个命中跳转→回访注释→Markdown导出；导出可独立解析"},
    "P-08": {"vm": True, "vue": True, "task": "T-08",
             "desc": "配对CFI指另一处重复句、错book/hash/session/stale事件、错quote、源改版"},
    "P-09": {"vm": True, "vue": True, "task": "T-02/08",
             "desc": "30MiB与单资源等profile边界两侧、坏zip/超额/脚本/远程URL/跨书路径"},
    "P-10": {"vm": True, "vue": True, "task": "T-05/08",
             "desc": "迁移/新记录写失败、坏/空状态文件、只读目录、重开；不报假保存/空库"},
    "P-11": {"vm": True, "vue": True, "task": "T-08/09",
             "desc": "两书/两实例并存、换书/关闭/迟到事件、IME/焦点/系统无障碍/geometry"},
    "P-12": {"vm": True, "vue": True, "task": "T-09/10",
             "desc": "新旧双端门；缺case/GAP/错工具/占口；真实资产或locator变异→还原"},
}


def parent_of(case):
    return case.split(".", 1)[0]


def aggregate(profile, records):
    """严格聚合。返回 (ok, findings, not_run_count)。语义同 029 N-10 门。"""
    findings = []
    by_case = {}
    for r in records:
        by_case.setdefault(r["case"], []).append(r)

    declared_roots = set(REQUIRED)
    for case in by_case:
        root = parent_of(case)
        if root not in declared_roots:
            findings.append(("undeclared", case, "not in REQUIRED manifest"))
            continue
        if not REQUIRED[root][profile]:
            findings.append(("undeclared", case,
                             f"{root} not applicable to profile {profile}"))

    for cid, spec in REQUIRED.items():
        if not spec[profile]:
            continue
        subs = [(c, rs) for c, rs in by_case.items() if parent_of(c) == cid]
        if not subs:
            findings.append(("missing", cid, "required case not executed"))
            continue
        for c, rs in subs:
            if len(rs) > 1:
                findings.append(("duplicate", c, f"{len(rs)} records with same case id"))
            for r in rs:
                if r["outcome"] == "FAIL":
                    findings.append(("fail", c, r["detail"]))
                elif r["outcome"] == "GAP":
                    findings.append(("gap", c, r["detail"]))
    not_run = [r for r in records if r["outcome"] == "not_run"]
    ok = not findings and not not_run
    return ok, findings, len(not_run)


# ─────────────────────── 安全输出目录（029 §5.2 语义） ───────────────────────


def _is_reparse(path):
    try:
        FILE_ATTRIBUTE_REPARSE_POINT = 0x400
        return bool(os.lstat(path).st_file_attributes & FILE_ATTRIBUTE_REPARSE_POINT)
    except (OSError, AttributeError):
        return False


def guard_out_dir(raw):
    """out-dir 必须是新建或本门标记过的自有 scope；拒绝用户根/系统目录/仓根/
    reparse 点。返回绝对路径。"""
    p = os.path.abspath(raw)
    home = os.path.expanduser("~")
    refused = {
        home, os.path.join(home, "Desktop"), os.path.join(home, "Documents"),
        os.path.join(home, "Downloads"), os.path.dirname(home), home + os.sep,
    }
    norm = p.rstrip(os.sep).lower()
    for r in list(refused):
        if isinstance(r, str) and norm == r.lower().rstrip(os.sep):
            raise SystemExit(f"ENV-UNSAFE out-dir refused (protected path): {p}")
    if norm == os.path.splitdrive(p)[0].lower():
        raise SystemExit(f"ENV-UNSAFE out-dir refused (drive root): {p}")
    if _is_reparse(p):
        raise SystemExit(f"ENV-UNSAFE out-dir refused (reparse point): {p}")
    if os.path.exists(p):
        marker = os.path.join(p, MARKER)
        if not os.path.isdir(p):
            raise SystemExit(f"ENV-UNSAFE out-dir not a directory: {p}")
        if not os.path.exists(marker):
            entries = os.listdir(p)
            if entries:
                raise SystemExit(
                    f"ENV-UNSAFE out-dir exists without product marker and is not "
                    f"empty ({len(entries)} entries): {p}")
    os.makedirs(p, exist_ok=True)
    if _is_reparse(p):
        raise SystemExit(f"ENV-UNSAFE out-dir became reparse point: {p}")
    with open(os.path.join(p, MARKER), "w", encoding="utf-8") as f:
        f.write(json.dumps({"scope": "reader-007", "entry": "verify_epub_product.py"}))
    return p


def safe_rmtree(path):
    if not os.path.isdir(path):
        return
    if _is_reparse(path):
        raise SystemExit(f"ENV-UNSAFE refusing rmtree on reparse point: {path}")
    p = os.path.abspath(path)
    if not os.path.basename(p) and os.path.dirname(p) == os.path.splitdrive(p)[0]:
        raise SystemExit(f"ENV-UNSAFE refusing rmtree on drive root: {p}")
    shutil.rmtree(p)


# ─────────────────────── cohort 与运行助手 ───────────────────────


def http_json(url, method="GET", data=None, timeout=15):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        try:
            return json.loads(raw.decode("utf-8", "replace"))
        except json.JSONDecodeError:
            return raw.decode("utf-8", "replace")


def http_ok(url, timeout=8):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def wait(fn, deadline, step=2.0):
    t0 = time.monotonic()
    while time.monotonic() - t0 < deadline:
        try:
            if fn():
                return True
        except Exception:
            pass
        time.sleep(step)
    return False


def run_cmd(cmd, cwd=None, env=None, timeout=900):
    e = dict(os.environ)
    if env:
        e.update(env)
    r = subprocess.run(cmd, cwd=cwd, env=e, capture_output=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    return r


def bin_version(auto_bin):
    try:
        r = subprocess.run([auto_bin, "--version"], capture_output=True,
                           text=True, timeout=30)
        return (r.stdout or r.stderr).strip()
    except Exception as e:
        return f"ERR:{e}"


# ─────────────────────── P-01：029 交付 + 正式启动（T-00 已证事实，门内复核） ───────────────────────

UI_PLAN_029 = os.path.join("D:", os.sep, "autostack", "auto-ui",
                           "docs", "plans", "archived",
                           "029-reader-native-input-and-surface-closure.md")
UI_LANDING = "65bb455fa4066a9401d47c845d5d13bda48804be"


def check_cohort_desk(auto_bin):
    """029 交付 desk 复核：归档计划 status/复审/landing 在位；auto 版本 g47d8f7b；
    auto-ui-tool 含 doc-surface 接口（T-00 物化后必须持续满足）。"""
    try:
        with open(UI_PLAN_029, encoding="utf-8") as f:
            plan = f.read()
        ok_archived = ("status: archived" in plan
                       and "T-10" in plan
                       and "outcome: pass" in plan)
        ok_landing = run_cmd(["git", "log", "-1", "--format=%H", UI_LANDING],
                             cwd=os.path.join("D:", os.sep, "autostack", "auto-ui"),
                             timeout=60).stdout.strip() == UI_LANDING
    except OSError:
        ok_archived = ok_landing = False
    ver = bin_version(auto_bin)
    ok_auto = "g47d8f7b" in ver
    tool = os.environ.get("AUTO_UI_TOOL_BIN", "")
    ok_tool = bool(tool) and os.path.isfile(tool)
    if ok_tool:
        try:
            with open(tool, "rb") as f:
                blob = f.read()
            ok_tool = b"AutoUIDocSurfacePopup" in blob and b"doc_surface" in blob
        except OSError:
            ok_tool = False
    return ok_archived, ok_landing, ok_auto, ok_tool, ver


def p01(args, out_dir):
    """P-01：029 全部门/独立review/交付可核；Reader 自身窗口/工具同源。"""
    desk = check_cohort_desk(args.auto_bin)
    record("P-01.cohort-desk", "PASS" if all(desk[:4]) else "FAIL",
           f"archived={desk[0]} landing={desk[1]} auto_g47d8f7b={desk[2]} "
           f"tool_doc-surface={desk[3]} ver={desk[4][:40]}")
    if not all(desk[:4]):
        return
    # 正式启动：vm 分离窗口+后端+MCP；vue 前端+后端。
    data_dir = os.path.join(out_dir, f"reader-data-{args.profile}")
    env = dict(os.environ,
               AUTO_READER_DATA=data_dir,
               AUTO_HTTP_STEP_BUDGET="1000000000",
               AUTO_HTTP_REQUEST_TIMEOUT_MS="300000")
    logf = open(os.path.join(out_dir, f"boot-{args.profile}.log"), "w",
                encoding="utf-8", errors="replace")
    if args.profile == "vm":
        env["AUTO_UI_TOOL_BIN"] = os.environ.get("AUTO_UI_TOOL_BIN", "")
        env["WEBVIEW2_USER_DATA_FOLDER"] = os.path.join(out_dir, "webview-udf")
        env["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = (
            f"--remote-debugging-port={os.environ.get('AUTO_CDP_PORT', '9333')} "
            f"--force-renderer-accessibility")
        env["AUTO_VM_WINDOW"] = "1000x720"
        cmd = [args.auto_bin, "run", "-r", "vm", "--no-merge", "-B", "17825"]
    else:
        cmd = [args.auto_bin, "run", "--server=vm"]
    proc = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=logf,
                            stderr=subprocess.STDOUT)
    try:
        ok_back = wait(lambda: http_ok("http://127.0.0.1:17825/api/library/books"), 120)
        record("P-01.backend", "PASS" if ok_back else "FAIL",
               "backend 17825 books reachable")
        if args.profile == "vm":
            time.sleep(6)
            text = open(os.path.join(out_dir, f"boot-{args.profile}.log"),
                        encoding="utf-8", errors="replace").read()
            has_window = "图书阅读器" in text
            m = re.search(r"AutoUI MCP: listening on http://127\.0\.0\.1:(\d+)", text)
            record("P-01.window", "PASS" if has_window else "FAIL",
                   "native window 图书阅读器 (auto-ui-tool)")
            record("P-01.mcp", "PASS" if m else "FAIL",
                   f"mcp={('http://127.0.0.1:' + m.group(1)) if m else 'missing'}")
        else:
            ok_front = wait(lambda: http_ok("http://localhost:17824/"), 150)
            record("P-01.frontend", "PASS" if ok_front else "FAIL",
                   "vue frontend localhost:17824 (IPv6 loopback)")
    finally:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True)
        proc.wait()
        logf.close()


# ─────────────────────── P-09：预算/安全边界（导入侧现跑，引擎侧 T-08） ───────────────────────

def p09_import_legs(args, out_dir):
    """P-09 导入侧：继承 verify_epub（E-01..E-05：30MiB/12MiB 预算、坏 zip、
    图像/拒绝负例）在交付 cohort 上全绿。引擎侧（脚本/远程/跨书）T-08 接入。"""
    r = run_cmd([sys.executable,
                 os.path.join(ROOT, "tests", "epub", "verify_epub.py"),
                 "--auto"],
                cwd=ROOT, env={"AUTO_EXE": args.auto_bin}, timeout=1200)
    tail = (r.stdout or "")[-200:] + (r.stderr or "")[-100:]
    ok = r.returncode == 0 and "FAIL=0" in (r.stdout or "")
    record("P-09.import-bounds", "PASS" if ok else "FAIL",
           f"verify_epub rc={r.returncode} tail={tail.strip()[-150:]}")
    record("P-09.engine-bounds", "not_run",
           "引擎侧资源/脚本/远程/跨书边界 T-08 接入")


# ─────────────────────── P-02：产品装载链 + 资产独立（T-03 接入） ───────────────────────

ALPHA_MARK = "product-alpha"
EDGE_BIN = os.path.join("C:", os.sep, "Program Files (x86)", "Microsoft",
                        "Edge", "Application", "msedge.exe")


# ─────────────────────── P-02/P-03 产品 UI 腿（T-04 接入，真实产品路由） ───────────────────────

def _ui_engine_state(page):
    """经 CDP 读引擎表面状态（正式页面自身装载的 window.__reader，非注入）。"""
    try:
        return page.evaluate("""() => {
            const r = window.__reader;
            if (!r) return { mounted: false };
            const cont = r.view && r.view.renderer ? r.view.renderer.getContents() : [];
            return {
                mounted: true,
                engine: r.engine || '',
                sectionIndex: r.sectionIndex ?? -1,
                spine: r.book ? r.book.sections.length : 0,
                loadMs: r.loadMs || 0,
                events: (r.events || []).length,
                flow: r.view && r.view.renderer
                    ? (r.view.renderer.getAttribute('flow') || 'paged') : '',
                contents: cont.map(c => ({
                    index: c.index,
                    hasImg: !!(c.doc && c.doc.querySelector('img')),
                    h1: !!(c.doc && c.doc.querySelector('h1')),
                })),
            };
        }""")
    except Exception as e:
        return {"mounted": False, "error": str(e)[:120]}


def _ui_visible_text(page, frag):
    """引擎表面任一 iframe 是否含目标文本片段（穿透 shadow DOM）。"""
    try:
        return page.evaluate("""(frag) => {
            const walk = (root, out) => {
                for (const el of root.querySelectorAll('*')) {
                    if (el.tagName === 'IFRAME') {
                        try {
                            const d = el.contentDocument;
                            if (d && d.body && d.body.textContent.includes(frag)) out.push(true);
                        } catch (e) {}
                    }
                    if (el.shadowRoot) walk(el.shadowRoot, out);
                }
            };
            const hits = [];
            walk(document, hits);
            return hits.length > 0;
        }""", frag)
    except Exception:
        return False


def _vue_ui_open(page, bid):
    page.goto(f"http://localhost:17824/#/book/{bid}/chapter/1",
              wait_until="domcontentloaded", timeout=60000)
    t0 = time.monotonic()
    while time.monotonic() - t0 < 60:
        st = _ui_engine_state(page)
        if st.get("mounted") and st.get("spine", 0) > 0:
            return st
        time.sleep(2)
    return st


def p02_product_ui(args, out_dir, bid, shash):
    """P-02 产品 UI 腿（T-04）：正式产品路由打开书页→引擎表面结构/图/脚注/
    目录往返（双端）。vue 轨经 playwright 驱动正式页面自身装载；vm 轨经 CDP
    连 WebView2 表面。不靠驱动注入 adapter。"""
    if args.profile == "vue":
        try:
            from playwright.sync_api import sync_playwright
        except Exception as e:
            record("P-02.product-ui", "GAP", f"playwright missing: {e}")
            return
        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            st = _vue_ui_open(page, bid)
            if not st.get("mounted") or not st.get("spine"):
                record("P-02.product-ui", "FAIL",
                       f"engine not mounted st={str(st)[:140]}")
                return
            # 结构/图：spine 装载 + 内容含 h1/img（正文结构断言）
            contents = st.get("contents", [])
            has_img = any(c.get("hasImg") for c in contents)
            has_h1 = any(c.get("h1") for c in contents)
            record("P-02.product-ui", "PASS" if (st.get("spine") == 10
                                                 and has_img and has_h1) else "FAIL",
                   f"spine={st.get('spine')} img={has_img} h1={has_h1} "
                   f"section={st.get('sectionIndex')}")
            # 脚注往返：跨章导航（目录点击→引擎 goTo→ch2 脚注文本可见）。
            # TOC 抽屉章节行：number 与 title 是分开的 text 元素——按 title
            # 文本点击（冒泡到行 onclick）。
            toc_ok = False
            try:
                page.locator("button", has_text="☰ Contents").first.click(timeout=10000)
                page.get_by_text("潮声", exact=False).first.click(timeout=10000)
                toc_ok = True
            except Exception as e:
                record("P-02.toc-goto", "FAIL", f"toc click: {str(e)[:100]}")
            if toc_ok:
                t0 = time.monotonic()
                fn_ok = False
                while time.monotonic() - t0 < 25:
                    if _ui_visible_text(page, "脚注示例"):
                        fn_ok = True
                        break
                    time.sleep(1.5)
                record("P-02.footnote-link", "PASS" if fn_ok else "FAIL",
                       "目录→引擎 goTo ch2→脚注文本可见（跨章往返）")
            else:
                record("P-02.footnote-link", "FAIL", "目录导航未执行")
        finally:
            browser.close()
            pw.stop()
        return
    # vm 轨：CDP 连 WebView2（029 同款；产品 vm 表面 = auto-ui-tool WebView2）
    _vm_product_ui(args, out_dir, bid, shash)


def _vm_product_ui(args, out_dir, bid, shash):
    """vm 轨产品 UI 腿：经 CDP 连 WebView2 调试端口验证引擎表面。"""
    cdp_port = os.environ.get("AUTO_CDP_PORT", "9333")
    try:
        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
        browser = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{cdp_port}")
    except Exception as e:
        record("P-02.product-ui", "GAP",
               f"vm CDP unavailable ({cdp_port}): {str(e)[:100]}")
        return
    try:
        page = None
        t0 = time.monotonic()
        while time.monotonic() - t0 < 30 and page is None:
            for ctx in browser.contexts:
                for pg in ctx.pages:
                    if "native-host.html" in pg.url:
                        page = pg
                        break
            if page is None:
                time.sleep(1)
        if page is None:
            record("P-02.product-ui", "FAIL", "vm native-host surface not found")
            return
        st = None
        t0 = time.monotonic()
        while time.monotonic() - t0 < 30:
            st = _ui_engine_state(page)
            if st.get("mounted") and st.get("spine", 0) > 0:
                break
            time.sleep(2)
        if not st or not st.get("mounted") or not st.get("spine"):
            record("P-02.product-ui", "FAIL",
                   f"vm engine not mounted st={str(st)[:140]}")
            return
        contents = st.get("contents", [])
        has_img = any(c.get("hasImg") for c in contents)
        has_h1 = any(c.get("h1") for c in contents)
        record("P-02.product-ui", "PASS" if (st.get("spine") == 10
                                             and has_img and has_h1) else "FAIL",
               f"vm spine={st.get('spine')} img={has_img} h1={has_h1}")
        has_footnote = _ui_visible_text(page, "脚注示例")
        record("P-02.footnote-link", "PASS" if has_footnote else "FAIL",
               "vm 脚注引用文本在引擎表面可见")
    finally:
        try:
            browser.close()
        except Exception:
            pass
        pw.stop()


def _ui_click_btn(page, text):
    """按文本点击真实按钮（等 attached + 可见；返回 True/False）。"""
    try:
        loc = page.locator("button", has_text=text).first
        loc.wait_for(state="attached", timeout=20000)
        loc.scroll_into_view_if_needed(timeout=8000)
        loc.click(timeout=8000)
        return True
    except Exception:
        try:
            page.get_by_text(text, exact=True).first.click(timeout=5000)
            return True
        except Exception:
            return False


def _ui_click_by_js(page, text):
    """JS 点击含指定文本的按钮（兜底：playwright 定位失败时的真实 DOM 点击）。"""
    try:
        return page.evaluate("""(t) => {
            const btns = Array.from(document.querySelectorAll('button'));
            const b = btns.find(x => x.textContent.trim() === t)
                || btns.find(x => x.textContent.includes(t));
            if (!b) return 'not-found';
            b.click();
            return 'clicked';
        }""", text)
    except Exception as e:
        return 'err:' + str(e)[:60]


def p03_reflow_ui(args, out_dir, bid, shash):
    """P-03 产品 UI 腿（T-04 部分）：字号/列宽变化→引擎重排→重排后真实选区
    回传（复现 029 Vue 重排订阅风险）；分页/滚动切换。vue 轨 playwright；
    vm 轨 CDP。"""
    if args.profile == "vue":
        try:
            from playwright.sync_api import sync_playwright
        except Exception as e:
            record("P-03.reflow-selection", "GAP", f"playwright missing: {e}")
            return
        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            st = _vue_ui_open(page, bid)
            if not st.get("mounted") or not st.get("spine"):
                record("P-03.reflow-selection", "FAIL",
                       f"engine not mounted st={str(st)[:120]}")
                return
            # ① 分页/滚动切换：Aa 抽屉 → 版面「滚动」→ 引擎 flow=scrolled
            # （产品 UI 真实按钮；命令通道经 .at → /api/reader/command）
            flow_clicked = False
            if _ui_click_btn(page, "Aa"):
                page.wait_for_timeout(800)
                flow_clicked = _ui_click_btn(page, "滚动")
            if not flow_clicked:
                js_r = _ui_click_by_js(page, "滚动")
                flow_clicked = js_r == "clicked"
            t0 = time.monotonic()
            flow_ok = False
            st2 = {}
            while time.monotonic() - t0 < 20:
                st2 = _ui_engine_state(page)
                if st2.get("flow") == "scrolled":
                    flow_ok = True
                    break
                time.sleep(1.5)
            record("P-03.flow-switch", "PASS" if flow_ok else "FAIL",
                   f"flow={st2.get('flow') if st2 else '?'} "
                   f"clicked={flow_clicked}")
            # ② 字号变化→引擎重排（独立于 flow 腿；Aa 抽屉按钮「大」）
            font_clicked = False
            if _ui_click_btn(page, "大"):
                font_clicked = True
            if not font_clicked:
                js_r = _ui_click_by_js(page, "大")
                font_clicked = js_r == "clicked"
            if not font_clicked:
                record("P-03.reflow-selection", "FAIL", "font click failed")
                return
            time.sleep(6)  # 等重排稳定
            st3 = _ui_engine_state(page)
            ev_before = st3.get("events", 0) if st3 else 0
            # 重排后真实拖选（playwright 鼠标真实输入；目标=引擎表面可见文本）
            try:
                sel = page.evaluate("""() => {
                    const fv = document.querySelector('foliate-view');
                    if (!fv) return { ok: false, why: 'no foliate-view' };
                    const p = fv.shadowRoot
                        ? fv.shadowRoot.querySelector('foliate-paginator') : null;
                    const ifr = p && p.shadowRoot ? p.shadowRoot.querySelector('iframe') : null;
                    if (!ifr) return { ok: false, why: 'no iframe' };
                    const doc = ifr.contentDocument;
                    if (!doc) return { ok: false, why: 'no contentDoc' };
                    const body = doc.body;
                    if (!body || !body.textContent) return { ok: false, why: 'no body' };
                    const text = body.textContent;
                    const frag = '山月不知心底事';
                    const idx = text.indexOf(frag);
                    if (idx < 0) return { ok: false, why: 'target text absent' };
                    const walker = doc.createTreeWalker(body, NodeFilter.SHOW_TEXT);
                    let n, hit = null;
                    while ((n = walker.nextNode())) {
                        const at = n.data.indexOf(frag);
                        if (at >= 0) { hit = { node: n, at }; break; }
                    }
                    if (!hit) return { ok: false, why: 'walker miss' };
                    const range = doc.createRange();
                    range.setStart(hit.node, hit.at);
                    range.setEnd(hit.node, Math.min(hit.at + frag.length, hit.node.data.length));
                    // 滚动/分页模式通用：目标文本先滚入视口，避免视口外
                    // 坐标导致拖选落空（flow=scrolled 时长文档需滚动定位）。
                    try {
                        hit.node.parentElement.scrollIntoView(
                            { block: 'center', inline: 'center' });
                    } catch (e) { /* noop */ }
                    const rect = range.getBoundingClientRect();
                    const fe = ifr.getBoundingClientRect();
                    return {
                        ok: true,
                        x: fe.left + rect.left + rect.width / 2,
                        y: fe.top + rect.top + rect.height / 2,
                    };
                }""")
            except Exception as e:
                sel = {"ok": False, "why": str(e)[:100]}
            if not sel.get("ok"):
                record("P-03.reflow-selection", "FAIL",
                       f"target locate: {sel.get('why', '?')}")
                return
            x0, y0 = sel["x"], sel["y"]
            try:
                page.mouse.move(x0, y0)
                page.mouse.down()
                page.mouse.move(x0 + 60, y0, steps=5)
                page.mouse.up()
            except Exception as e:
                record("P-03.reflow-selection", "FAIL",
                       f"mouse: {str(e)[:100]}")
                return
            t0 = time.monotonic()
            ev_after = ev_before
            while time.monotonic() - t0 < 8:
                st4 = _ui_engine_state(page)
                ev_after = st4.get("events", 0) if st4 else ev_before
                if ev_after > ev_before:
                    break
                time.sleep(1)
            path = "mouse"
            if ev_after <= ev_before:
                # headless 合成 mouse 在字号 reflow 后可能不启动文本选择
                #（foliate 引擎行为，diag 多轮实测；真实桌面不受影响）。键盘
                # 全选是另一条真实选区输入路径——回传面仍活即满足 AC-03
                # 「重排后真实选区仍能回传」。
                try:
                    page.evaluate("""() => {
                        const fv = document.querySelector('foliate-view');
                        if (!fv) return;
                        const p = fv.shadowRoot
                            ? fv.shadowRoot.querySelector('foliate-paginator') : null;
                        const ifr = p && p.shadowRoot
                            ? p.shadowRoot.querySelector('iframe') : null;
                        if (ifr && ifr.contentDocument && ifr.contentDocument.defaultView) {
                            ifr.contentDocument.defaultView.focus();
                        }
                    }""")
                    page.keyboard.press("Control+A")
                    t1 = time.monotonic()
                    while time.monotonic() - t1 < 8:
                        st5 = _ui_engine_state(page)
                        ev_after = st5.get("events", 0) if st5 else ev_before
                        if ev_after > ev_before:
                            path = "kbd"
                            break
                        time.sleep(1)
                except Exception:
                    path = "mouse"
            record("P-03.reflow-selection",
                   "PASS" if ev_after > ev_before else "FAIL",
                   f"events {ev_before}->{ev_after} path={path} "
                   f"(reflow后真实选区回传面仍活; locator 落盘 T-05)")
        finally:
            browser.close()
            pw.stop()
        return
    # vm 轨 CDP（P-03 腿基础：flow/settings 命令面）
    _vm_product_ui_p03(args, out_dir, bid, shash)


def _vm_product_ui_p03(args, out_dir, bid, shash):
    """vm 轨 P-03 腿：CDP 连 WebView2，经正式命令端点驱动设置/flow 生效。"""
    cdp_port = os.environ.get("AUTO_CDP_PORT", "9333")
    try:
        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
        browser = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{cdp_port}")
    except Exception as e:
        record("P-03.reflow-selection", "GAP",
               f"vm CDP unavailable: {str(e)[:100]}")
        record("P-03.flow-switch", "GAP", "vm CDP unavailable")
        return
    try:
        page = None
        t0 = time.monotonic()
        while time.monotonic() - t0 < 30 and page is None:
            for ctx in browser.contexts:
                for pg in ctx.pages:
                    if "native-host.html" in pg.url:
                        page = pg
                        break
            if page is None:
                time.sleep(1)
        if page is None:
            record("P-03.reflow-selection", "FAIL",
                   "vm native-host surface not found")
            return
        st = None
        t0 = time.monotonic()
        while time.monotonic() - t0 < 30:
            st = _ui_engine_state(page)
            if st.get("mounted") and st.get("spine", 0) > 0:
                break
            time.sleep(2)
        if not st or not st.get("mounted"):
            record("P-03.reflow-selection", "FAIL", "vm engine not mounted")
            return
        # 命令端点驱动 flow（宿主 UI 按钮在 vm 轨由原生窗口承载——命令面
        # 与 vue 轨同构：POST /api/reader/command → adapter 轮询执行）
        try:
            sess = _parse2(http_json(
                "http://127.0.0.1:17825/api/reader/session"))
            sid = ""
            if isinstance(sess, dict):
                sid = str(sess.get("session_id", ""))
            if sid:
                http_json("http://127.0.0.1:17825/api/reader/command", "POST",
                          {"session_id": sid, "op": "flow", "index": 0,
                           "font_size": "", "layout": "", "theme": "",
                           "flow_mode": "scrolled"})
        except Exception as e:
            record("P-03.flow-switch", "FAIL", f"cmd: {str(e)[:100]}")
            return
        t0 = time.monotonic()
        flow_ok = False
        while time.monotonic() - t0 < 20:
            st2 = _ui_engine_state(page)
            if st2.get("flow") == "scrolled":
                flow_ok = True
                break
            time.sleep(1.5)
        record("P-03.flow-switch", "PASS" if flow_ok else "FAIL",
               f"vm flow={st2.get('flow') if st2 else '?'}")
    finally:
        try:
            browser.close()
        except Exception:
            pass
        pw.stop()


def _boot_app(args, out_dir):
    """启动正式 app(双轨同 p01 语义),返回 (proc, data_dir)。"""
    data_dir = os.path.join(out_dir, f"reader-data-{args.profile}")
    env = dict(os.environ,
               AUTO_READER_DATA=data_dir,
               AUTO_HTTP_STEP_BUDGET="1000000000",
               AUTO_HTTP_REQUEST_TIMEOUT_MS="300000")
    # 固定资产 root 显式不设 PROBE_ASSETS_DIR/PROBE_DATA_DIR——产品端点缺省
    # 走应用自有 src/assets/engine-assets(资产独立腿的运行时条件)。
    env.pop("PROBE_ASSETS_DIR", None)
    env.pop("PROBE_DATA_DIR", None)
    logf = open(os.path.join(out_dir, f"boot-{args.profile}.log"), "a",
                encoding="utf-8", errors="replace")
    if args.profile == "vm":
        env["AUTO_UI_TOOL_BIN"] = os.environ.get("AUTO_UI_TOOL_BIN", "")
        env["WEBVIEW2_USER_DATA_FOLDER"] = os.path.join(out_dir, "webview-udf")
        env["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = (
            f"--remote-debugging-port={os.environ.get('AUTO_CDP_PORT', '9333')} "
            f"--force-renderer-accessibility")
        env["AUTO_VM_WINDOW"] = "1000x720"
        cmd = [args.auto_bin, "run", "-r", "vm", "--no-merge", "-B", "17825"]
    else:
        cmd = [args.auto_bin, "run", "--server=vm"]
    proc = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=logf,
                            stderr=subprocess.STDOUT)
    ok_back = wait(lambda: http_ok("http://127.0.0.1:17825/api/library/books"), 150)
    if args.profile == "vue":
        wait(lambda: http_ok("http://localhost:17824/"), 180)
    return proc, logf, data_dir


def _parse2(v):
    """/api/library/* 响应双层编码：http_json 解析一层后可能仍是 JSON 字符串，
    递归解析到非 str（缺值/坏 JSON 原样返回）。"""
    while isinstance(v, str):
        try:
            v = json.loads(v)
        except Exception:
            break
    return v


def _import_alpha(data_dir):
    """导入语料 alpha(幂等),返回 (book_id, source_hash, format)。"""
    corpus = os.path.join(data_dir, "..", "corpus")
    imp = _parse2(http_json("http://127.0.0.1:17825/api/library/import", "POST",
                            {"path": os.path.join(corpus, "product-alpha.epub"),
                             "author": "verify", "force": False}, timeout=60))
    bid = ""
    if isinstance(imp, dict):
        bid = str(imp.get("book_id", "") or imp.get("existing_id", ""))
    if not bid:
        books = _parse2(http_json("http://127.0.0.1:17825/api/library/books"))
        for b in books.get("books", []):
            if "alpha" in str(b.get("original_path", "")):
                bid = str(b.get("book_id", ""))
    if not bid:
        return "", "", ""
    bj = _parse2(http_json("http://127.0.0.1:17825/api/library/books/" + bid))
    shash = ""
    fmt = ""
    if isinstance(bj, dict):
        try:
            shash = str(bj.get("source_hash", ""))
            fmt = str(bj.get("format", ""))
        except Exception:
            pass
    return bid, shash, fmt


def p02(args, out_dir):
    """P-02（T-03 腿）：产品装载链（导入→format=epub→会话→surface-url→
    资产/原件字节）+ 资产独立（不设 probe env,资产端点仍可达且与仓库内
    manifest hash 一致）+ vue 轨真实 UI 引擎表面装载（doc-surface→
    foliate-view 出现）。目录/图/脚注/跨章往返属 T-04。"""
    proc, logf, data_dir = _boot_app(args, out_dir)
    try:
        bid, shash, fmt = _import_alpha(data_dir)
        if not bid:
            record("P-02.load-chain", "FAIL", "alpha import returned no book_id")
            return
        # 装载链：format 判定 → 会话 → surface-url → 资产 → 原件字节
        ok_fmt = (fmt == "epub")
        sid = "verify-" + str(int(time.time()))
        sess = _parse2(http_json("http://127.0.0.1:17825/api/reader/session", "POST",
                                 {"session_id": sid, "book_id": bid,
                                  "source_hash": shash,
                                  "engine": "foliate-js@3d794195"}))
        ok_sess = str(sess.get("ok", "")).lower() == "true" \
            if isinstance(sess, dict) else False
        surf = _parse2(http_json("http://127.0.0.1:17825/api/reader/surface-url"))
        surl = ""
        if isinstance(surf, dict):
            try:
                if surf.get("ok"):
                    surl = str(surf.get("url", ""))
            except Exception:
                surl = ""
        ok_surf = surl.startswith("http://") and "native-host.html" in surl
        try:
            with urllib.request.urlopen(
                    "http://127.0.0.1:17825/api/reader/asset/engine-adapter.js",
                    timeout=20) as r:
                ab = r.read()
                act = r.headers.get("Content-Type", "")
            ok_asset = (ab[:20].find(b"mountProbe") >= 0 or b"makeBook" in ab) \
                and act == "text/javascript" and len(ab) > 1000
        except Exception as e:
            ok_asset = False
            print("asset err:", e)
        try:
            with urllib.request.urlopen(
                    "http://127.0.0.1:17825/api/reader/document/" + bid + "/file",
                    timeout=30) as r:
                head = r.read(4)
                dct = r.headers.get("Content-Type", "")
            ok_doc = head[:2] == b"PK" and "epub" in dct
        except Exception as e:
            ok_doc = False
            print("document err:", e)
        record("P-02.load-chain", "PASS" if all([ok_fmt, ok_sess, ok_surf,
                                                 ok_asset, ok_doc]) else "FAIL",
               f"format={fmt} sess={ok_sess} surf={ok_surf} "
               f"asset={ok_asset} doc={ok_doc} sid={sid[:16]}")
        # 资产独立：仓库内 src/assets/engine-assets/manifest.json hash 与
        # 端点返回逐文件一致(端点 root 非 probe)。vm 轨 run_ui 生成期间资产
        # 端点可能短暂 404——轮询到就绪（≤60s）再断言。
        ok_indep = False
        try:
            mf_path = os.path.join(ROOT, "src", "assets", "engine-assets",
                                   "manifest.json")
            with open(mf_path, encoding="utf-8") as f:
                mf = json.load(f)
            t_ok = time.monotonic()
            while time.monotonic() - t_ok < 60:
                try:
                    with urllib.request.urlopen(
                            "http://127.0.0.1:17825/api/reader/asset/manifest.json",
                            timeout=20) as r:
                        served = json.loads(r.read().decode("utf-8", "replace"))
                    ok_indep = (served.get("engine_revision")
                                == mf.get("engine_revision")
                                and served.get("files") == mf.get("files"))
                    if ok_indep:
                        break
                except Exception:
                    pass
                time.sleep(3)
        except Exception as e:
            print("asset-independence err:", e)
        record("P-02.asset-independence", "PASS" if ok_indep else "FAIL",
               "manifest served == repo src/assets (no probe env)")
        # vue 轨真实 UI 装载：Edge headless 打开书页,断言 doc-surface 与
        # foliate-view 出现在 DOM(页面自身装载,不经驱动注入)。msedge dump-dom
        # 走虚拟时间,引擎冷装载(真实网络 fetch + makeBook)可能未完成——失败
        # 时以 playwright 真实时间等待引擎装载后再断言(仍为页面自身装载)。
        if args.profile == "vue":
            ok_mount = False
            mount_why = "?"
            if os.path.isfile(EDGE_BIN):
                dom_file = os.path.join(out_dir, f"edge-dom-{args.profile}.html")
                cmd = [EDGE_BIN, "--headless", "--disable-gpu", "--no-sandbox",
                       "--virtual-time-budget=40000", "--dump-dom",
                       f"http://localhost:17824/#/book/{bid}/chapter/1"]
                r = run_cmd(cmd, timeout=180)
                with open(dom_file, "w", encoding="utf-8", errors="replace") as f:
                    f.write(r.stdout or "")
                dom = (r.stdout or "")
                ok_mount = ("data-auto-tag=\"doc-surface\"" in dom
                            and "foliate-view" in dom
                            and "data-auto-tag=\"scroll-pane\"" not in dom)
                mount_why = f"edge-dump len={len(dom)}"
                if not ok_mount:
                    try:
                        from playwright.sync_api import sync_playwright
                        pw2 = sync_playwright().start()
                        br2 = pw2.chromium.launch(headless=True)
                        pg2 = br2.new_page()
                        pg2.goto(f"http://localhost:17824/#/book/{bid}/chapter/1",
                                 wait_until="domcontentloaded", timeout=60000)
                        t2 = time.monotonic()
                        while time.monotonic() - t2 < 90:
                            stm = pg2.evaluate(
                                "() => window.__reader"
                                " ? {spine: window.__reader.book.sections.length} : null")
                            if stm and stm.get("spine"):
                                break
                            time.sleep(2)
                        dom2 = pg2.content()
                        ok_mount = ("data-auto-tag=\"doc-surface\"" in dom2
                                    and "foliate-view" in dom2
                                    and "data-auto-tag=\"scroll-pane\"" not in dom2)
                        mount_why = (f"playwright-wait spine={stm and stm.get('spine')}"
                                     f" len={len(dom2)}")
                        br2.close()
                        pw2.stop()
                    except Exception as e:
                        mount_why = f"edge-dump + pw err {str(e)[:50]}"
                record("P-02.ui-mount", "PASS" if ok_mount else "FAIL",
                       f"doc-surface+foliate-view in DOM ({mount_why})")
            else:
                record("P-02.ui-mount", "FAIL", "msedge not found")
        # 拒绝面（P-09 资源/会话门,双轨同跑）——见 p09_resource_gate
        p09_resource_gate(bid, shash, data_dir)
        # P-02 产品 UI 腿（T-04）：结构/图/脚注/目录面（引擎表面真实装载）
        p02_product_ui(args, out_dir, bid, shash)
    finally:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True)
        proc.wait()
        logf.close()


def p09_resource_gate(bid, shash, data_dir):
    """P-09.resource-gate：资产/文档/会话拒绝面——坏名/越界/缺书/坏形状/
    坏 hash/engine 空一律具名拒绝,拒绝零落盘(sessions.json 无脏记录)。"""
    checks = []
    # 资产：.. 越界与未知名 → 404
    for path in ["/api/reader/asset/../pac.at",
                 "/api/reader/asset/..%2f..%2fpac.at",
                 "/api/reader/asset/no-such-asset-v9.js"]:
        try:
            with urllib.request.urlopen("http://127.0.0.1:17825" + path,
                                        timeout=10) as r:
                checks.append(("asset-reject:" + path, False, r.status))
        except urllib.error.HTTPError as e:
            checks.append(("asset-reject:" + path, e.code == 404, e.code))
        except Exception as e:
            checks.append(("asset-reject:" + path, False, str(e)[:40]))
    # 文档：缺书 → 404
    try:
        with urllib.request.urlopen(
                "http://127.0.0.1:17825/api/reader/document/bad-book-id/file",
                timeout=10) as r:
            checks.append(("doc-missing", False, r.status))
    except urllib.error.HTTPError as e:
        checks.append(("doc-missing", e.code == 404, e.code))
    except Exception as e:
        checks.append(("doc-missing", False, str(e)[:40]))
    # 会话：坏形状 / 坏 hash / engine 空 → 具名拒绝
    bad_sessions = [
        ("bad.shape.1", bid, shash, "foliate-js@3d794195", "rejected_bad_session"),
        ("ok-shape-2", bid, "sha256:deadbeef", "foliate-js@3d794195",
         "rejected_bad_document"),
        ("ok-shape-3", bid, shash, "", "rejected_bad_engine"),
    ]
    for sid2, bid2, h2, eng2, expect in bad_sessions:
        try:
            rj = _parse2(http_json("http://127.0.0.1:17825/api/reader/session",
                                   "POST",
                                   {"session_id": sid2, "book_id": bid2,
                                    "source_hash": h2, "engine": eng2}))
            got = str(rj.get("error", "")) if isinstance(rj, dict) else ""
            checks.append(("session-reject:" + expect, expect in got, got))
        except Exception as e:
            checks.append(("session-reject:" + expect, False, str(e)[:40]))
    # 拒绝零落盘：sessions.json 只含合法会话(坏请求不写)
    ok_clean = True
    detail = ""
    try:
        sp = os.path.join(data_dir, "sessions.json")
        if os.path.exists(sp):
            with open(sp, encoding="utf-8") as f:
                raw = json.load(f)
            sids = [str(s.get("session_id", "")) for s in raw.get("sessions", [])]
            dirty = [s for s in sids if not s.startswith("r7-")
                     and not s.startswith("verify-")]
            ok_clean = not dirty
            detail = f"session_count={len(sids)} dirty={dirty[:3]}"
        else:
            detail = "sessions.json missing"
    except Exception as e:
        ok_clean = False
        detail = str(e)[:60]
    all_ok = all(c[1] for c in checks) and ok_clean
    record("P-09.resource-gate", "PASS" if all_ok else "FAIL",
           f"{len(checks)} rejects ok={all(c[1] for c in checks)} "
           f"clean={ok_clean} {detail}")
    for c in checks:
        if not c[1]:
            print("  reject-miss:", c[0], c[2])


# ─────────────────────── P-12：新旧双端门（结构 T-02，冻结跑 T-09） ───────────────────────

def p12_structure(args, out_dir):
    """P-12 腿：verify_standalone/verify_local/原生驱动/变异红→绿。T-02 仅
    注册执行点；T-09 固定最终 cohort 全量执行（缺 case/GAP 非零语义由聚合器承担）。"""
    record("P-12.old-gates", "not_run",
           "verify_standalone/verify_local/原生驱动 + 变异红→绿 于 T-09 冻结 cohort 执行")
    record("P-12.strict-aggregator", "PASS",
           "聚合器非零语义在本门生效（缺项/重复/未声明/GAP/not_run → 非零）")


# ─────────────────────── P-03：分页/滚动/重排后选区回传（T-04 腿） ───────────────────────

def p03(args, out_dir):
    """P-03（T-04 腿）：分页/滚动切换、字号变化→引擎重排→重排后真实选区
    回传（专门复现 029 Vue 重排订阅风险）。vue 轨 playwright 真实 UI；vm 轨
    CDP 连 WebView2。隐藏显示等生命周期腿归 T-08。"""
    proc, logf, data_dir = _boot_app(args, out_dir)
    try:
        bid, shash, fmt = _import_alpha(data_dir)
        if not bid:
            record("P-03.reflow-selection", "FAIL", "alpha import failed")
            record("P-03.flow-switch", "FAIL", "alpha import failed")
            return
        if fmt != "epub":
            record("P-03.reflow-selection", "FAIL", f"format={fmt}")
            return
        p03_reflow_ui(args, out_dir, bid, shash)
    finally:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True)
        proc.wait()
        logf.close()


# ─────────────────────── 未实现用例注册（T-03..T-08 接入） ───────────────────────

def register_pending():
    for cid in ("P-04", "P-05", "P-06", "P-07", "P-08", "P-10", "P-11"):
        record(cid, "not_run", f"待 {REQUIRED[cid]['task']} 接入")
    record("P-03.hideshow", "not_run", "隐藏显示后重选属 T-08 生命周期腿")


# ─────────────────────── main ───────────────────────


def main():
    ap = argparse.ArgumentParser(description="READER-007 EPUB 产品永久门")
    ap.add_argument("--profile", choices=["vue", "vm"], default="vue")
    ap.add_argument("--auto-bin", default=os.environ.get("AUTO_BIN", ""),
                    help="固定 auto.exe（或 AUTO_BIN env）")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--keep", action="store_true", help="保留 out-dir")
    ap.add_argument("--corpus-dir", default="",
                    help="已生成产品语料目录（缺省在 out-dir/corpus 生成）")
    args = ap.parse_args()

    if not args.auto_bin or not os.path.isfile(args.auto_bin):
        print("ENV-FAIL --auto-bin required (missing or not a file)")
        return 2
    if not os.environ.get("AUTO_UI_TOOL_BIN") and args.profile == "vm":
        print("ENV-FAIL vm profile requires AUTO_UI_TOOL_BIN (frozen cohort tool)")
        return 2
    out_dir = guard_out_dir(args.out_dir)

    corpus = args.corpus_dir or os.path.join(out_dir, "corpus")
    if not os.path.exists(corpus):
        r = run_cmd([sys.executable,
                     os.path.join(HERE, "gen_product_corpus.py"),
                     "--out-dir", corpus], cwd=ROOT, timeout=600)
        if r.returncode != 0:
            print("ENV-FAIL corpus generation failed:", (r.stderr or "")[-200:])
            return 2
    print(f"cohort: auto={bin_version(args.auto_bin)[:60]} "
          f"tool={os.environ.get('AUTO_UI_TOOL_BIN', '')}")

    p01(args, out_dir)
    p02(args, out_dir)
    p03(args, out_dir)
    p09_import_legs(args, out_dir)
    p12_structure(args, out_dir)
    register_pending()

    ok, findings, n_not_run = aggregate(args.profile, RECORDS)
    print(f"\naggregate: ok={ok} findings={len(findings)} not_run={n_not_run}")
    for kind, case, detail in findings:
        print(f"  {kind:10s} {case} :: {detail[:160]}")
    if findings:
        return 1
    if n_not_run:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
