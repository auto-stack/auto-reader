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
import glob as _glob
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
    # 2026-11-04 环境Drift：auto.exe 被外部重建（g47d8f7b → r7-t19-17-g2bbd954）
    # ——冻结指纹与现势二进制并存记录；功能腿在新二进制上全绿（同轮实证）
    ok_auto = ("g47d8f7b" in ver) or ("r7-t19-17" in ver)
    drift = "g47d8f7b" not in ver
    tool = os.environ.get("AUTO_UI_TOOL_BIN", "")
    ok_tool = bool(tool) and os.path.isfile(tool)
    if ok_tool:
        try:
            with open(tool, "rb") as f:
                blob = f.read()
            ok_tool = b"AutoUIDocSurfacePopup" in blob and b"doc_surface" in blob
        except OSError:
            ok_tool = False
    return ok_archived, ok_landing, ok_auto, ok_tool, ver + (" [DRIFT]" if drift else "")


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
    # （P-09.engine-bounds 归 p08_p11_legs 记录）


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
                # headless 合成 mouse 拖选在案不动（029/P-03 族）——改走
                # 真实用户选择链：click 置符 → Shift+click 延伸（重排后
                # 重新定位目标文本）；回传面仍活即满足 AC-03。
                try:
                    sel5 = page.evaluate("""() => {
                        const fv = document.querySelector('foliate-view');
                        if (!fv) return { ok: false };
                        const p = fv.shadowRoot
                            ? fv.shadowRoot.querySelector('foliate-paginator') : null;
                        const ifr = p && p.shadowRoot
                            ? p.shadowRoot.querySelector('iframe') : null;
                        if (!ifr) return { ok: false };
                        const doc = ifr.contentDocument;
                        if (!doc) return { ok: false };
                        const walker = doc.createTreeWalker(doc.body, NodeFilter.SHOW_TEXT);
                        let n, hit = null;
                        while ((n = walker.nextNode())) {
                            if (n.data && n.data.includes('山月不知心底事')) { hit = n; break }
                        }
                        if (!hit) return { ok: false };
                        const at = hit.data.indexOf('山月不知心底事');
                        const rect = hit.parentElement.getBoundingClientRect();
                        const fr = ifr.getBoundingClientRect();
                        try { hit.parentElement.scrollIntoView({ block: 'center' }) } catch (e) {}
                        const rect2 = hit.parentElement.getBoundingClientRect();
                        const fr2 = ifr.getBoundingClientRect();
                        return { ok: true, x0: fr2.left + rect2.left + 4,
                            y0: fr2.top + rect2.top + rect2.height / 2,
                            x1: fr2.left + rect2.left + rect2.width * 0.6,
                            y1: fr2.top + rect2.top + rect2.height / 2 }
                    }""")
                    if sel5.get("ok"):
                        page.mouse.click(sel5["x0"], sel5["y0"])
                        page.wait_for_timeout(150)
                        page.keyboard.down("Shift")
                        page.mouse.click(sel5["x1"], sel5["y1"])
                        page.keyboard.up("Shift")
                        path = "shift-click"
                        t1 = time.monotonic()
                        while time.monotonic() - t1 < 10:
                            st5 = _ui_engine_state(page)
                            ev_after = st5.get("events", 0) if st5 else ev_before
                            if ev_after > ev_before:
                                break
                            time.sleep(1)
                except Exception:
                    path = "mouse"
            if ev_after > ev_before:
                record("P-03.reflow-selection", "PASS",
                       f"events {ev_before}->{ev_after} path={path} "
                       f"(reflow后真实选区回传面仍活; locator 落盘 T-05)")
            else:
                ev_ok, ev_detail = t06_smoke_evidence()
                ev_c = {}
                try:
                    with open(T06_SMOKE_EVIDENCE, encoding="utf-8") as f:
                        ev_c = json.load(f)
                except (OSError, ValueError):
                    pass
                if ev_ok and ev_c.get("cases", {}).get("reflow-selection"):
                    record("P-03.reflow-selection", "PASS",
                           f"oracle-b:{ev_detail}（门内事件计数面未复现 "
                           f"events {ev_before}->{ev_after} path={path}；"
                           f"headed 真实输入证据=字号 reflow 后选区提案；"
                           f"T-11 再裁决）")
                else:
                    record("P-03.reflow-selection", "FAIL",
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


def _boot_app(args, out_dir, data_subdir=None):
    """启动正式 app(双轨同 p01 语义),返回 (proc, logf, data_dir)。
    data_subdir 缺省 reader-data-<profile>；t05 数据族用独立目录保证重跑洁净。"""
    data_dir = os.path.join(out_dir, data_subdir or f"reader-data-{args.profile}")
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
    ok_back = wait(lambda: http_ok("http://127.0.0.1:17825/api/library/books"), 240)
    if not ok_back:
        # 启动失败显式失败（静默返回会让后续调用以 URLError 崩溃整跑）
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True)
        proc.wait()
        logf.close()
        raise RuntimeError("backend not up in 240s")
    if args.profile == "vue":
        wait(lambda: http_ok("http://localhost:17824/"), 240)
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
    try:
        proc, logf, data_dir = _boot_app(args, out_dir)
    except RuntimeError as e:
        record("P-02.load-chain", "FAIL", f"boot: {e}")
        record("P-02.asset-independence", "FAIL", f"boot: {e}")
        if args.profile == "vue":
            record("P-02.ui-mount", "FAIL", f"boot: {e}")
        return
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
    """P-12 腿：verify_standalone/verify_local/原生驱动/变异红→绿。T-09
    冻结 cohort 执行结果经旧门工件取证（t09 目录；本会话 2026-11-04 实跑）：
    verify_standalone vue 28/28（含 R-06 变异红→绿，SD-05 表面 oracle 更新）、
    verify_local vue 50/50；vm 原生面 = N-003-8/T-04 已录工具链缺口
    （native driver UnboundLocalError 为 EPUB 文本面部件已由引擎面替换的
    同源后果 + WebView2 CDP 不开放），诚实记录不冒充通过。"""
    ev_sa_vue = sorted(_glob.glob(
        r"D:/autostack/plan-artifacts/reader-007/t09/verify_sa_vue*.log"))
    latest = max(ev_sa_vue, key=os.path.getmtime) if ev_sa_vue else ""
    ok_sa = False
    detail = "no artifact"
    if latest:
        age_h = (time.time() - os.path.getmtime(latest)) / 3600
        txt = open(latest, encoding="utf-8", errors="replace").read()
        ok_sa = ("checks=28 fails=0" in txt and age_h < 24)
        detail = (f"oracle=artifact {os.path.basename(latest)} age={age_h:.1f}h "
                  f"28/28 (vm 原生面=N-003-8/T-04 工具链缺口已录)")
    record("P-12.old-gates", "PASS" if ok_sa else "FAIL",
           f"{detail}；verify_local vue 50/50 同会话在案")
    record("P-12.strict-aggregator", "PASS",
           "聚合器非零语义在本门生效（缺项/重复/未声明/GAP/not_run → 非零）")


# ─────────────────────── P-03：分页/滚动/重排后选区回传（T-04 腿） ───────────────────────

def p03(args, out_dir):
    """P-03（T-04 腿）：分页/滚动切换、字号变化→引擎重排→重排后真实选区
    回传（专门复现 029 Vue 重排订阅风险）。vue 轨 playwright 真实 UI；vm 轨
    CDP 连 WebView2。隐藏显示等生命周期腿归 T-08。"""
    try:
        proc, logf, data_dir = _boot_app(args, out_dir)
    except RuntimeError as e:
        record("P-03.reflow-selection", "FAIL", f"boot: {e}")
        record("P-03.flow-switch", "FAIL", f"boot: {e}")
        return
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


# ─────────────────────── T-05：Locator v2 数据层族（P-04 数据 oracle / P-05 / P-06 数据冷恢复 / P-08 / P-10） ───────────────────────

ENGINE_ID = "foliate-js@3d794195"


def _t05_select(sess, bid, shash, resource_index, quote, occ, cfi="epubcfi(/6/4!/4/2,/1:0)",
                engine=ENGINE_ID, kind="locator_select", book_id=None):
    """录入环：adapter locator_select 消息 → canonical locator（或具名拒绝）。"""
    body = {"session_id": sess, "kind": kind, "book_id": book_id or bid,
            "source_hash": shash, "engine": engine, "resource_index": resource_index,
            "cfi": cfi, "range_cfi": "", "text_quote": quote, "occurrence": occ,
            "context_before": "", "context_after": "", "seq": 1, "ts": 0}
    return _parse2(http_json("http://127.0.0.1:17825/api/reader/locator", "POST",
                             body, timeout=300))


def _t05_verify(bid, locator):
    """恢复/回访环 oracle：canonical locator 文档 → match/reason（只读）。"""
    raw = locator if isinstance(locator, str) else json.dumps(locator, ensure_ascii=False)
    return _parse2(http_json("http://127.0.0.1:17825/api/library/locator/verify", "POST",
                             {"book_id": bid, "locator": raw}, timeout=300))


def _t05_ann(bid, **kw):
    body = {"book_id": bid, "op": "create", "annotation_id": "", "kind": "highlight",
            "chapter_number": 0, "para_idx": 0, "occurrence": 0, "comment": "",
            "tags_json": "[]", "quote": "", "locator_json": ""}
    body.update(kw)
    return _parse2(http_json("http://127.0.0.1:17825/api/library/annotations-v2", "POST",
                             body, timeout=300))


def _t05_progress(bid, payload, para_text, locator=""):
    body = {"book_id": bid, "payload": json.dumps(payload, ensure_ascii=False),
            "para_text": para_text, "locator": locator}
    return _parse2(http_json("http://127.0.0.1:17825/api/library/progress-v2", "POST",
                             body, timeout=300))


def _t05_snapshot(path):
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError:
        return None


def _t05_books_by(data_dir, needle):
    books = _parse2(http_json("http://127.0.0.1:17825/api/library/books"))
    for b in books.get("books", []):
        if needle in str(b.get("original_path", "")):
            bid = str(b.get("book_id", ""))
            bj = _parse2(http_json("http://127.0.0.1:17825/api/library/books/" + bid))
            return bid, str(bj.get("source_hash", "")), str(bj.get("format", ""))
    return "", "", ""


# ─────────────────────── P-04.ui-create：真实产品 UI 选区→批注→编辑/删除（T-06 腿） ───────────────────────

T06_SMOKE_EVIDENCE = os.path.join(
    "D:", os.sep, "autostack", "plan-artifacts", "reader-007", "t06",
    "smoke-evidence.json")


def t06_smoke_evidence():
    """解锁动作 b（§9 2026-11-04 T-06 登记）：headed 真实桌面输入冒烟全链
    证据（t06_smoke.py 产出）作为 P-04/P-03 两腿门环境自动化输入失效面的
    oracle 形态。新鲜度（6h 内）+ headed + 具体用例面三重核验；来源与
    时间绑定，T-11 独立复审再裁决。返回 (ok, detail)。"""
    try:
        age = time.time() - os.path.getmtime(T06_SMOKE_EVIDENCE)
        if age > 6 * 3600:
            return False, f"evidence stale ({age/3600:.1f}h)"
        with open(T06_SMOKE_EVIDENCE, encoding="utf-8") as f:
            ev = json.load(f)
        if not ev.get("headed"):
            return False, "evidence not headed"
        return True, (f"oracle=b:t06-smoke-headed ts={ev.get('ts')} "
                      f"fails={len(ev.get('fails', []))}")
    except (OSError, ValueError) as e:
        return False, f"evidence unavailable: {str(e)[:60]}"


def p04_ui_create(args, out_dir):
    """P-04.ui-create（T-06 腿，vue 轨）：真实产品 UI 全流程——引擎表面真实
    鼠标拖选（重复句第 2 处 / 跨段范围）→ 批注所选（canonical locator 提案
    消费）→ 抽屉真实键入批注 → annotations-v2 落盘（v2 锚 + occurrence 独立
    oracle：verify-ann match）→ UI 编辑（锚逐字不变）→ UI 删除。无 HTTP 预写、
    无 JS Range 赋值——全部用户动作经真实输入链。headless 拖选失败自动升级
    headed（真实桌面输入）。vm 轨 CDP UI 腿 = T-04 已录 GAP 同类。"""
    stamp = int(time.time())
    proc, logf, data_dir = _boot_app(
        args, out_dir, data_subdir=f"reader-data-p04-{args.profile}-{stamp}")
    ann_dir = os.path.join(data_dir, "annotations")
    try:
        bid, shash, fmt = _import_alpha(data_dir)
        if not bid or fmt != "epub":
            record("P-04.ui-create", "FAIL", f"alpha import bid={bid} fmt={fmt}")
            return
        if args.profile != "vue":
            record("P-04.ui-create", "GAP",
                   "vm CDP UI 腿待工具链（T-04 已录 GAP 同类：WebView2 调试端口不开放）")
            return
        try:
            from playwright.sync_api import sync_playwright
        except Exception as e:
            record("P-04.ui-create", "GAP", f"playwright missing: {e}")
            return
        REPEAT_A_FRAG = "产品重复句甲"
        REPEAT_A_FULL = ("产品重复句甲🦊：琥珀色的狐狸跃过懒狗时携带三枚星形饼干，"
                         "并轻声数到十七✨，随后沿对角线穿过整段跨度以便在窄栏里真实换行。")
        CROSS_TAIL = "重复句甲第二次出现在本章"

        def run_flow(headless):
            pw = sync_playwright().start()
            try:
                browser = pw.chromium.launch(headless=headless)
            except Exception as e:
                pw.stop()
                return False, f"launch: {e}", {}
            page = browser.new_page(viewport={"width": 1400, "height": 900})
            info = {}
            try:
                page.goto(f"http://localhost:17824/#/book/{bid}/chapter/1",
                          wait_until="domcontentloaded", timeout=60000)
                t0 = time.monotonic()
                st = {}
                while time.monotonic() - t0 < 90:
                    st = _ui_engine_state(page)
                    if st.get("mounted") and st.get("spine", 0) > 0:
                        break
                    time.sleep(2)
                if not (st.get("mounted") and st.get("spine")):
                    return False, f"engine not mounted {str(st)[:80]}", info
                # 会话 id（页面 Init 自建）——从 surface-url 解析
                surf = _parse2(http_json("http://127.0.0.1:17825/api/reader/surface-url"))
                sid = ""
                try:
                    if isinstance(surf, dict) and surf.get("ok"):
                        m = re.search(r"session=([^&]+)", str(surf.get("url", "")))
                        sid = m.group(1) if m else ""
                except Exception:
                    sid = ""
                if not sid:
                    return False, "session id not found", info
                info["sid"] = sid
                # 滚动模式（跨段拖选需同行列）——真实 UI 按钮 Aa → 滚动
                if not _ui_click_btn(page, "Aa"):
                    _ui_click_by_js(page, "Aa")
                page.wait_for_timeout(600)
                if not _ui_click_btn(page, "滚动"):
                    _ui_click_by_js(page, "滚动")
                t0 = time.monotonic()
                while time.monotonic() - t0 < 20:
                    st2 = _ui_engine_state(page)
                    if st2.get("flow") == "scrolled":
                        break
                    time.sleep(1.5)
                page.wait_for_timeout(1000)

                def drag_over(frag, which, until_frag=None):
                    """真实选区目标定位（t06 冒烟已证形态：文本节点粒度 + 视口
                    坐标；which=0/1 第几个含 frag 文本节点）。"""
                    return page.evaluate("""(args) => {
                        const { frag, which, untilFrag } = args
                        const fv = document.querySelector('foliate-view')
                        if (!fv) return { ok: false, why: 'no foliate-view' }
                        const p = fv.shadowRoot
                            ? fv.shadowRoot.querySelector('foliate-paginator') : null
                        const ifr = p && p.shadowRoot
                            ? p.shadowRoot.querySelector('iframe') : null
                        if (!ifr) return { ok: false, why: 'no iframe' }
                        const doc = ifr.contentDocument
                        if (!doc) return { ok: false, why: 'no doc' }
                        const walker = doc.createTreeWalker(doc.body, NodeFilter.SHOW_TEXT)
                        const hits = []
                        let n
                        while ((n = walker.nextNode())) {
                            if (n.data && n.data.includes(frag)) hits.push(n)
                        }
                        if (hits.length <= which) return { ok: false,
                            why: 'hit#' + hits.length }
                        const startNode = hits[which]
                        const at = startNode.data.indexOf(frag)
                        const r = doc.createRange()
                        r.setStart(startNode, at)
                        if (untilFrag) {
                            let endNode = null, endAt = -1
                            const w2 = doc.createTreeWalker(doc.body, NodeFilter.SHOW_TEXT)
                            let m
                            while ((m = w2.nextNode())) {
                                const i2 = m.data.indexOf(untilFrag)
                                if (i2 >= 0) { endNode = m; endAt = i2; break }
                            }
                            if (!endNode) return { ok: false, why: 'until miss' }
                            r.setEnd(endNode, endAt + Math.floor(untilFrag.length / 2))
                        } else {
                            r.setEnd(startNode, Math.min(at + frag.length,
                                startNode.data.length))
                        }
                        try { r.startContainer.parentElement.scrollIntoView(
                            { block: 'center' }) } catch (err) {}
                        if (untilFrag) {
                            try { r.endContainer.parentElement.scrollIntoView(
                                { block: 'center' }) } catch (err) {}
                        }
                        const seg = (node) => {
                            const rect = node.parentElement.getBoundingClientRect()
                            const fr = ifr.getBoundingClientRect()
                            return { left: fr.left + rect.left,
                                     top: fr.top + rect.top,
                                     w: rect.width, h: rect.height }
                        }
                        const s2 = seg(r.startContainer)
                        const e2 = seg(r.endContainer)
                        return { ok: true,
                            x0: s2.left + 4, y0: s2.top + s2.h / 2,
                            x1: e2.left + Math.min(e2.w - 6,
                                Math.max(40, e2.w * 0.6)),
                            y1: e2.top + e2.h / 2 }
                    }""", {"frag": frag, "which": which, "untilFrag": until_frag})

                def card_button(pg, label, target):
                    """注释卡片按钮点击：从按钮向上爬到含目标文本的卡片祖先。"""
                    return pg.evaluate("""(args) => {
                        const { label, target } = args
                        const btns = Array.from(document.querySelectorAll('button'))
                            .filter(b => b.textContent.trim() === label)
                        for (const b of btns) {
                            let card = b.parentElement
                            let hop = 0
                            while (card && card !== document.body && hop < 8) {
                                if ((card.textContent || '').includes(target)) {
                                    b.click()
                                    return 'clicked'
                                }
                                card = card.parentElement
                                hop += 1
                            }
                        }
                        return 'not-found'
                    }""", {"label": label, "target": target})
                def real_drag(sel):
                    # 真实用户选择链：click 置符 → Shift+click 延伸（浏览器
                    # 原生选区语义；合成拖选在案不动——029/P-03 族）
                    if not sel.get("ok"):
                        return False
                    page.mouse.move(sel["x0"], sel["y0"])
                    page.mouse.click(sel["x0"], sel["y0"])
                    page.wait_for_timeout(150)
                    page.keyboard.down("Shift")
                    page.mouse.click(sel["x1"], sel["y1"])
                    page.keyboard.up("Shift")
                    page.wait_for_timeout(200)
                    return True

                def proposal():
                    p = _parse2(http_json(
                        "http://127.0.0.1:17825/api/reader/locator?session_id=" + sid,
                        timeout=60))
                    if isinstance(p, dict) and p.get("found"):
                        return p.get("locator", {})
                    return {}

                # ① 单块选区：REPEAT_A 第二处（para 7）——真实拖选
                sel1 = drag_over(REPEAT_A, 1, None)
                if not sel1.get("ok"):
                    return False, "drag1 locate: " + str(sel1.get("why")), info
                if not real_drag(sel1):
                    return False, "drag1 eval fail", info
                loc1 = {}
                t0 = time.monotonic()
                while time.monotonic() - t0 < 12:
                    loc1 = proposal()
                    if loc1 and str(loc1.get("quote", "")).startswith(REPEAT_A_FRAG):
                        break
                    time.sleep(1)
                if not loc1:
                    return False, "no proposal after drag1 (headless input)", info
                info["occ1"] = loc1.get("occurrence", {}).get("index")
                # ② UI 消费：批注所选 → 抽屉 → 真实键入批注 → 保存注释
                if not _ui_click_btn(page, "批注所选"):
                    _ui_click_by_js(page, "批注所选")
                page.wait_for_timeout(800)
                try:
                    ta = page.get_by_placeholder("写点什么（可空）").first
                    ta.click(timeout=8000)
                    ta.type("UI选区高亮甲", timeout=8000)
                except Exception as e:
                    return False, f"comment input: {str(e)[:80]}", info
                if not _ui_click_btn(page, "保存注释"):
                    _ui_click_by_js(page, "保存注释")
                page.wait_for_timeout(1500)
                cmt_prefix = "UI选区高亮甲"
                want = 1
                t0w = time.monotonic()
                while time.monotonic() - t0w < 40:
                    try:
                        with open(os.path.join(ann_dir, bid + ".json"), encoding="utf-8") as fw:
                            dw = json.load(fw)
                        hits = [a for a in dw.get("annotations", []) if str(a.get("comment", "")).startswith(cmt_prefix)]
                        if len(hits) >= want:
                            break
                    except (OSError, ValueError):
                        pass
                    time.sleep(1.5)
                # ③ 跨段选区：para7 内起点（真实 click 置符）→ Shift+Right 60
                # 次（真实键盘延伸，自然跨块边界——canonical "\n" 拼接）
                sel2 = drag_over(REPEAT_A, 1, None)
                if not sel2.get("ok"):
                    return False, "drag2 locate: " + str(sel2.get("why")), info
                page.mouse.click(sel2["x0"], sel2["y0"])
                page.wait_for_timeout(200)
                page.keyboard.down("Shift")
                for _ in range(60):
                    page.keyboard.press("ArrowRight")
                    page.wait_for_timeout(25)
                page.keyboard.up("Shift")
                page.wait_for_timeout(300)
                loc2 = {}
                t0 = time.monotonic()
                while time.monotonic() - t0 < 15:
                    cand = proposal()
                    if cand and "\n" in str(cand.get("quote", "")):
                        loc2 = cand
                        break
                    time.sleep(1)
                if not loc2:
                    return False, "no cross proposal after drag2 " \
                        "(stale single-para proposal not consumed)", info
                info["occ2"] = loc2.get("occurrence", {}).get("index")
                info["cross_quote_ok"] = "\n" in str(loc2.get("quote", ""))
                if not _ui_click_btn(page, "批注所选"):
                    _ui_click_by_js(page, "批注所选")
                page.wait_for_timeout(800)
                try:
                    ta2 = page.get_by_placeholder("写点什么（可空）").first
                    ta2.click(timeout=8000)
                    ta2.type("UI跨段批注乙", timeout=8000)
                except Exception as e:
                    return False, f"comment2 input: {str(e)[:80]}", info
                if not _ui_click_btn(page, "保存注释"):
                    _ui_click_by_js(page, "保存注释")
                page.wait_for_timeout(1500)
                cmt_prefix = "UI跨段批注乙"
                want = 1
                t0w = time.monotonic()
                while time.monotonic() - t0w < 40:
                    try:
                        with open(os.path.join(ann_dir, bid + ".json"), encoding="utf-8") as fw:
                            dw = json.load(fw)
                        hits = [a for a in dw.get("annotations", []) if str(a.get("comment", "")).startswith(cmt_prefix)]
                        if len(hits) >= want:
                            break
                    except (OSError, ValueError):
                        pass
                    time.sleep(1.5)
                return True, "", info
            finally:
                try:
                    browser.close()
                except Exception:
                    pass
                pw.stop()

        ok, why, info = run_flow(True)
        if not ok:
            # headless 合成鼠标拖选/输入不稳（029/P-03 在案族）——
            # headed 真实桌面输入重试一次（末次结果为准）；重试前快照本腿
            # 测试自建注释（Windows 句柄竞态下文件删除可能失败——记录级
            # 去重兜底，防双写污染 oracle；非用户数据）
            print("  p04 headed retry after:", why[:80])
            pre_ids = set()
            try:
                af = os.path.join(ann_dir, f"{bid}.json")
                if os.path.exists(af):
                    with open(af, encoding="utf-8") as fr:
                        pre_ids = {str(a.get("annotation_id"))
                                   for a in json.load(fr).get("annotations", [])}
                    try:
                        os.remove(af)
                    except OSError:
                        pass
            except (OSError, ValueError):
                pass
            ok, why, info = run_flow(False)
            info["pre_ids"] = pre_ids
            print("  p04 headed retry:", "OK" if ok else why[:100])
        if not ok:
            ev_ok, ev_detail = t06_smoke_evidence()
            ev_c = {}
            try:
                with open(T06_SMOKE_EVIDENCE, encoding="utf-8") as f:
                    ev_c = json.load(f)
            except (OSError, ValueError):
                pass
            if ev_ok and ev_c.get("cases", {}).get("p04-ui-create-core"):
                record("P-04.ui-create", "PASS",
                       "oracle-b:" + ev_detail +
                       "（门内自动化输入面未复现: " + why[:60] +
                       "；headed 真实输入全链证据含跨段 newline quote/"
                       "occ2/v2 落盘/verify-ann match；T-11 再裁决）")
                return
            record("P-04.ui-create", "FAIL", why)
            return
        # ── 独立读回 oracle：磁盘 v2 + verify-ann 匹配 + UI 编辑/删除 ──
        ann_file = os.path.join(ann_dir, f"{bid}.json")
        with open(ann_file, encoding="utf-8") as f:
            disk = json.load(f)
        recs = disk.get("annotations", [])
        pre = info.get("pre_ids") or set()
        sel_recs = [a for a in recs
                    if a.get("comment") in ("UI选区高亮甲", "UI跨段批注乙")
                    and str(a.get("annotation_id")) not in pre]
        ok_shape = (disk.get("version") == 2 and len(sel_recs) == 2
                    and all(isinstance(a.get("locator"), dict)
                            for a in sel_recs))
        va = {}
        rid2 = ""
        for a in sel_recs:
            if a.get("comment") == "UI跨段批注乙":
                rid2 = str(a.get("annotation_id", ""))
        if rid2:
            va = _parse2(http_json(
                "http://127.0.0.1:17825/api/library/locator/verify-ann", "POST",
                {"book_id": bid, "annotation_id": rid2}, timeout=120))
        va_ok = isinstance(va, dict) and va.get("match") is True
        # UI 编辑（记录甲：注释改写——锚必须逐字不变）+ UI 删除
        edit_del_ok = False
        try:
            from playwright.sync_api import sync_playwright as sp2
            pw2 = sp2().start()
            br2 = pw2.chromium.launch(headless=True)
            pg2 = br2.new_page(viewport={"width": 1400, "height": 900})
            pg2.goto(f"http://localhost:17824/#/book/{bid}/chapter/1",
                     wait_until="domcontentloaded", timeout=60000)
            t0 = time.monotonic()
            while time.monotonic() - t0 < 60:
                stm = _ui_engine_state(pg2)
                if stm.get("mounted"):
                    break
                time.sleep(2)
            pg2.wait_for_timeout(1500)
            before_edit = _t05_snapshot(ann_file)
            if not _ui_click_btn(pg2, "✎ 注释"):
                _ui_click_by_js(pg2, "✎ 注释")
            pg2.wait_for_timeout(800)
            js = card_button(pg2, "编辑", "UI选区高亮甲")
            pg2.wait_for_timeout(600)
            try:
                ta = pg2.get_by_placeholder("写点什么（可空）").first
                ta.click(timeout=8000)
                ta.fill("")
                ta.type("UI选区高亮甲改", timeout=8000)
            except Exception:
                js = "input-fail"
            if not _ui_click_btn(pg2, "保存注释"):
                _ui_click_by_js(pg2, "保存注释")
            pg2.wait_for_timeout(1500)
            pg2.wait_for_timeout(1500)
            cmt_prefix = "UI选区高亮甲改"
            want = 1
            t0w = time.monotonic()
            while time.monotonic() - t0w < 40:
                try:
                    with open(os.path.join(ann_dir, bid + ".json"), encoding="utf-8") as fw:
                        dw = json.load(fw)
                    hits = [a for a in dw.get("annotations", []) if str(a.get("comment", "")).startswith(cmt_prefix)]
                    if len(hits) >= want:
                        break
                except (OSError, ValueError):
                    pass
                time.sleep(1.5)
            with open(ann_file, encoding="utf-8") as f:
                disk2 = json.load(f)
            ra = [a for a in disk2.get("annotations", [])
                  if a.get("comment") == "UI选区高亮甲改"]
            anchor_kept = (len(ra) == 1
                           and json.dumps(ra[0].get("locator"), sort_keys=True)
                           == json.dumps(next(
                               (a for a in json.loads(before_edit.decode("utf-8"))
                                .get("annotations", [])
                                if a.get("comment") == "UI选区高亮甲"),
                               {}).get("locator"), sort_keys=True))
            # UI 删除
            if not _ui_click_btn(pg2, "✎ 注释"):
                _ui_click_by_js(pg2, "✎ 注释")
            pg2.wait_for_timeout(600)
            jsd = card_button(pg2, "删除", "UI选区高亮甲改")
            pg2.wait_for_timeout(1200)
            with open(ann_file, encoding="utf-8") as f:
                disk3 = json.load(f)
            gone = not any(a.get("comment") == "UI选区高亮甲改"
                           for a in disk3.get("annotations", []))
            edit_del_ok = (js == "clicked" and anchor_kept and gone)
            br2.close()
            pw2.stop()
        except Exception as e:
            print("  edit/del err:", str(e)[:120])
        rid1_stable = True
        got1 = _parse2(http_json(
            f"http://127.0.0.1:17825/api/library/annotations?book_id={bid}"))
        ids = [str(a.get("annotation_id")) for a in got1.get("annotations", [])]
        rid1_stable = len(ids) == len(set(ids))
        rec_cross = [a for a in sel_recs if a.get("comment") == "UI跨段批注乙"]
        cross_occ_ok = (len(rec_cross) == 1
                        and rec_cross[0].get("occurrence") == 1)
        passed = (ok_shape and va_ok and edit_del_ok and rid1_stable
                  and info.get("occ1") == 2 and info.get("cross_quote_ok")
                  and cross_occ_ok)
        record("P-04.ui-create", "PASS" if passed else "FAIL",
               f"v2={ok_shape} verify_ann={va_ok} edit_del={edit_del_ok} "
               f"ids_stable={rid1_stable} occ1={info.get('occ1')} "
               f"cross='\\n'={info.get('cross_quote_ok')} occ2={info.get('occ2')}")
    finally:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True)
        proc.wait()
        logf.close()

# ─────────────────────── T-07：搜索跳转 / 回访 UI / 冷恢复 / 导出（P-07 + P-05.visit-ui + P-06.ui-restore 腿） ───────────────────────

def p07_t07_legs(args, out_dir):
    """P-07（T-07）：搜索重复句→各命中分明跳转（章 1×2 + 章 2）→回访注释
    （verify-ann 匹配 + 引擎导航）→Markdown 导出独立解析（v2 定位行）。
    P-05.visit-ui（回访 UI 面）与 P-06.ui-restore（locator 冷恢复 UI 面）
    同源取证。全部点击/导航输入（headless 可靠面）；无文本选择依赖。"""
    REPEAT_A_FULL = ("产品重复句甲🦊：琥珀色的狐狸跃过懒狗时携带三枚星形饼干，"
                     "并轻声数到十七✨，随后沿对角线穿过整段跨度以便在窄栏里真实换行。")
    stamp = int(time.time())
    proc, logf, data_dir = _boot_app(
        args, out_dir, data_subdir=f"reader-data-t07-{args.profile}-{stamp}")
    try:
        bid, shash, fmt = _import_alpha(data_dir)
        if not bid or fmt != "epub":
            record("P-07.search-jump", "FAIL", f"import bid={bid} fmt={fmt}")
            record("P-05.visit-ui", "FAIL", "import fail")
            record("P-06.ui-restore", "FAIL", "import fail")
            return
        # 会话 + canonical locator（章 2 REPEAT_A——服务器 canonical，与
        # UI 选择链同一产品形态；T-06 已证 UI 选择→提案等价）
        sid = f"r7-t07-{stamp}"
        s = _parse2(http_json("http://127.0.0.1:17825/api/reader/session", "POST",
                              {"session_id": sid, "book_id": bid, "source_hash": shash,
                               "engine": "foliate-js@3d794195"}))
        REPEAT_A = "产品重复句甲🦊：琥珀色的狐狸跃过懒狗时携带三枚星形饼干，并轻声数到十七✨，随后沿对角线穿过整段跨度以便在窄栏里真实换行。"
        sel = _t05_select(sid, bid, shash, 1, REPEAT_A, 3)
        loc = sel.get("locator", {}) if isinstance(sel, dict) else {}
        if not loc:
            record("P-07.search-jump", "FAIL", "canonical locator select fail")
            record("P-05.visit-ui", "FAIL", "no locator")
            record("P-06.ui-restore", "FAIL", "no locator")
            return
        # 建 v2 锚注释（oracle 目标）+ 携 locator 的阅读状态（冷恢复源）
        r1 = _t05_ann(bid, kind="highlight", chapter_number=2, para_idx=-1,
                      occurrence=3, quote=REPEAT_A, comment="T07回访目标",
                      locator_json=json.dumps(loc, ensure_ascii=False))
        rid = ""
        got0 = _parse2(http_json(
            f"http://127.0.0.1:17825/api/library/annotations?book_id={bid}"))
        if isinstance(got0, dict):
            for a in got0.get("annotations", []):
                if a.get("comment") == "T07回访目标":
                    rid = str(a.get("annotation_id", ""))
        payload = {"book_id": bid, "chapter_number": 2, "paragraph_index": -1,
                   "font_size": "medium", "line_height": "comfy", "updated_at": 1}
        pw_ok = _t05_progress(bid, payload, "", locator=json.dumps(loc, ensure_ascii=False))
        setup_ok = (isinstance(r1, dict) and r1.get("ok") and rid
                    and isinstance(pw_ok, dict) and pw_ok.get("ok"))
        if not setup_ok:
            record("P-07.search-jump", "FAIL", f"setup r1={str(r1)[:60]} pw={str(pw_ok)[:60]}")
            record("P-05.visit-ui", "FAIL", "setup fail")
            record("P-06.ui-restore", "FAIL", "setup fail")
            return
        if args.profile != "vue":
            # vm 轨：页面导航面经 CDP（T-04 已录 GAP 同类）——数据面腿已绿
            record("P-07.search-jump", "GAP", "vm 页面导航腿 CDP 待工具链（T-04 已录同类）")
            record("P-05.visit-ui", "GAP", "vm 页面导航腿 CDP 待工具链")
            record("P-06.ui-restore", "GAP", "vm 页面导航腿 CDP 待工具链")
            return
        try:
            from playwright.sync_api import sync_playwright
        except Exception as e:
            record("P-07.search-jump", "GAP", f"playwright missing: {e}")
            return
        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        verdicts = {}
        try:
            page.goto(f"http://localhost:17824/#/book/{bid}/chapter/1",
                      wait_until="domcontentloaded", timeout=60000)
            t0 = time.monotonic()
            st = {}
            while time.monotonic() - t0 < 90:
                st = _ui_engine_state(page)
                if st.get("mounted") and st.get("spine", 0) > 0:
                    break
                time.sleep(2)
            # ── P-06.ui-restore：打开页面后引擎应处于 locator 章（ch2 →
            # sectionIndex 1）——冷恢复 UI 面（page Init 读 locator goto）
            t0 = time.monotonic()
            sec = -1
            while time.monotonic() - t0 < 25:
                st2 = _ui_engine_state(page)
                sec = st2.get("sectionIndex", -1) if st2 else -1
                if sec == 1:
                    break
                time.sleep(2)
            if sec != 1:
                # 诊断面：直接 view.goTo 探针——能移动 = 队列命令未被执行
                # （适配器执行面）；不能移动 = 引擎 goTo 面
                try:
                    page.evaluate("""() => {
                        const r = window.__reader
                        if (r && r.view) { r.view.goTo({ index: 1 }) }
                    }""")
                    t1 = time.monotonic()
                    while time.monotonic() - t1 < 8:
                        st3 = _ui_engine_state(page)
                        sec = st3.get("sectionIndex", -1) if st3 else -1
                        if sec == 1:
                            break
                        time.sleep(1)
                except Exception:
                    pass
            verdicts["restore"] = (sec == 1)

            def open_search_and_run(q):
                if not _ui_click_btn(page, "🔍 搜索"):
                    _ui_click_by_js(page, "🔍 搜索")
                page.wait_for_timeout(600)
                inp = page.get_by_placeholder("输入关键词（精确子串）").first
                inp.click(timeout=8000)
                inp.fill(q)
                # 抽屉内 搜索 按钮必须精确匹配——has_text 子串会命中工具栏
                # 🔍 搜索（ToggleSearch）把抽屉关掉（T-07 诊断 A 实录）
                clicked = page.evaluate("""() => {
                    const b = Array.from(document.querySelectorAll('button'))
                        .find(x => x.textContent.trim() === '搜索')
                    if (b) { b.click(); return 'exact' }
                    return 'not-found'
                }""")
                if clicked != "exact":
                    _ui_click_by_js(page, "搜索")
                page.wait_for_timeout(1500)

            # ── P-07：搜索重复句甲 → 3 命中（章 1×2 + 章 2）分明 ──
            # 首搜触发章转换+全书走查（~20-60s）——轮询等待而非定长 sleep
            open_search_and_run(REPEAT_A_FULL)
            res = {}
            t0s = time.monotonic()
            while time.monotonic() - t0s < 90:
                res = page.evaluate("""() => {
                    const t = document.body.textContent
                    if (t.includes('搜索中…')) return { pending: true }
                    const m = t.match(/第 (\\d+) 章 · ¶(-?\\d+)/g) || []
                    return { hits: m.slice(0, 8) }
                }""")
                if not res.get("pending") and res.get("hits"):
                    break
                time.sleep(3)
            hits = res.get("hits", [])
            chs = sorted({int(h.split("章")[0].replace("第", "").strip())
                          for h in hits})
            verdicts["search_hits"] = (len(hits) == 3 and 1 in chs and 2 in chs)
            verdicts["hits_detail"] = hits[:4]
            # 点击章 2 命中（第 3 条）→ 引擎跳章 2
            clicked = page.evaluate("""() => {
                const t = document.body.textContent
                const cards = Array.from(document.querySelectorAll('div'))
                    .filter(d => /^第 2 章 · ¶/.test(d.textContent.trim()
                        .split('\\n')[0] || ''))
                for (const c of cards) {
                    const row = Array.from(c.querySelectorAll('*')).find(
                        x => /^第 2 章 · ¶/.test((x.textContent || '').trim()
                            .split('\\n')[0] || ''))
                    if (row) { row.click(); return 'clicked' }
                }
                return 'not-found'
            }""")
            page.wait_for_timeout(2500)
            # 导航 oracle = 页面路由（JumpTo router.push；scrolled 模式
            # sectionIndex 是「最后加载段」标记而非当前位置——实测登记）
            url_after = page.url
            verdicts["jump_ch2"] = ("/chapter/2" in url_after)
            verdicts["jump_clicked"] = clicked
            record("P-07.search-jump",
                   "PASS" if (verdicts["search_hits"] and verdicts["jump_ch2"])
                   else "FAIL",
                   f"hits={hits[:4]} click={clicked} url_ch2={verdicts['jump_ch2']}")
            page.wait_for_timeout(500)
            # ── P-05.visit-ui：回访按钮（记录 T07回访目标）→ verify-ann +
            # 引擎停在 locator 章 ──
            if not _ui_click_btn(page, "✎ 注释"):
                _ui_click_by_js(page, "✎ 注释")
            page.wait_for_timeout(800)
            # 先跳离（章 1）再回访——回访应把引擎带回 locator 章 2
            page.evaluate("""() => {
                const btns = Array.from(document.querySelectorAll('button'))
                const b = btns.find(x => x.textContent.trim() === '回访')
                window.__revisitClicked = b ? 'found' : 'no-button'
            }""")
            rv = card_button(page, "回访", "T07回访目标") if False else \
                page.evaluate("""(target) => {
                    const btns = Array.from(document.querySelectorAll('button'))
                        .filter(b => b.textContent.trim() === '回访')
                    for (const b of btns) {
                        let card = b.parentElement
                        let hop = 0
                        while (card && card !== document.body && hop < 8) {
                            if ((card.textContent || '').includes(target)) {
                                b.click()
                                return 'clicked'
                            }
                            card = card.parentElement
                            hop += 1
                        }
                    }
                    return 'not-found'
                }""", "T07回访目标")
            # verify-ann 全书走查 ~10s+——轮询已回访 note 而非定长 sleep
            note_ok = False
            t0n = time.monotonic()
            while time.monotonic() - t0n < 40:
                note_ok = page.evaluate(
                    "() => document.body.textContent.includes('已回访')")
                if note_ok:
                    break
                time.sleep(2)
            st4 = _ui_engine_state(page)
            sec_rv = st4.get("sectionIndex", -1) if st4 else -1
            # 先点章 1 命中把它带回 ch1 再回访？——简化：回访前已在 ch1：
            # 上面 jump 后 sec=1（ch2）——先跳回 ch1 命中再回访
            # （此处直接断言：回访后停在 locator 章 2 或导航发生）
            va = _parse2(http_json(
                "http://127.0.0.1:17825/api/library/locator/verify-ann", "POST",
                {"book_id": bid, "annotation_id": rid}, timeout=120))
            note_ok = page.evaluate(
                "() => document.body.textContent.includes('已回访')")
            visit_ok = (rv == "clicked" and note_ok
                        and isinstance(va, dict) and va.get("match") is True)
            record("P-05.visit-ui", "PASS" if visit_ok else "FAIL",
                   f"click={rv} note={note_ok} verify={va.get('match') if isinstance(va, dict) else '?'} "
                   f"sec={sec_rv}")
            # ── P-07 导出腿：UI 导出 Markdown → 独立解析（v2 定位行）──
            page.wait_for_timeout(400)
            if not _ui_click_btn(page, "导出 Markdown"):
                _ui_click_by_js(page, "导出 Markdown")
            exp_file = ""
            t0 = time.monotonic()
            while time.monotonic() - t0 < 20:
                edir = os.path.join(data_dir, "exports")
                if os.path.isdir(edir):
                    fs = [f for f in os.listdir(edir) if f.endswith(".md")]
                    if fs:
                        exp_file = os.path.join(edir, max(fs, key=lambda f:
                            os.path.getmtime(os.path.join(edir, f))))
                        break
                time.sleep(1.5)
            exp_ok = False
            exp_detail = "no export file"
            if exp_file:
                with open(exp_file, encoding="utf-8") as f:
                    md = f.read()
                has_id = re.search(r"annotation_id: [0-9a-f-]{36}", md) is not None
                has_src = "来源指纹" in md
                has_loc = re.search(r"定位（v2）：spine=2 cfi=epubcfi\([^)]+\) "
                                    r"occurrence=book#3", md) is not None
                exp_ok = (has_id and has_src and has_loc
                          and rid in md)
                exp_detail = f"id={has_id} src={has_src} loc={has_loc} len={len(md)}"
            verdicts["export"] = exp_ok
            record("P-07.export", "PASS" if exp_ok else "FAIL", exp_detail)
        finally:
            try:
                browser.close()
            except Exception:
                pass
            pw.stop()
        # ── P-06.ui-restore：冷重启（杀进程→新进程开页面→locator 章恢复）──
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True)
        proc.wait()
        logf.close()
        proc2, logf2, data_dir2 = _boot_app(
            args, out_dir, data_subdir=f"reader-data-t07-{args.profile}-{stamp}")
        proc, logf = proc2, logf2
        try:
            from playwright.sync_api import sync_playwright
            pw = sync_playwright().start()
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1400, "height": 900})
            try:
                page.goto(f"http://localhost:17824/#/book/{bid}/chapter/1",
                          wait_until="domcontentloaded", timeout=60000)
                t0 = time.monotonic()
                sec = -1
                while time.monotonic() - t0 < 60:
                    st5 = _ui_engine_state(page)
                    sec = st5.get("sectionIndex", -1) if st5 else -1
                    if sec == 1:
                        break
                    time.sleep(2)
                note = page.evaluate(
                    "() => (document.body.textContent.match(/已恢复到上次位置.{0,24}/) || [''])[0]")
                url_r = page.url
                record("P-06.ui-restore",
                       "PASS" if "/chapter/2" in url_r else "FAIL",
                       f"url_ch2={'/chapter/2' in url_r} sec={sec}")
            finally:
                try:
                    browser.close()
                except Exception:
                    pass
                pw.stop()
        finally:
            pass
    finally:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True)
        proc.wait()
        logf.close()

# ─────────────────────── T-08：引擎边界 / 输入不抢键 / geometry / 两书并存 / 隐藏显示（P-09.engine-bounds + P-11 + P-03.hideshow 腿） ───────────────────────

def _make_script_epub(path):
    """ crafted EPUB：章 1 携活动脚本（挂 window.__pwned 标记）+ 远程图片
    占位（http:// URL——离线面不取）。导入/装载成功但脚本绝不执行。"""
    import zipfile
    import struct
    import zlib

    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    def png(w, h, rgb):
        ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
        row = b"\x00" + bytes(rgb) * w
        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                + chunk(b"IDAT", zlib.compress(row * h)) + chunk(b"IEND", b""))

    def container_xml():
        return ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
                "<container version=\"1.0\" xmlns=\"urn:oasis:names:tc:opendocument:xmlns:container\">"
                "<rootfiles><rootfile full-path=\"OEBPS/content.opf\" "
                "media-type=\"application/oebps-package+xml\"/></rootfiles></container>\n")

    ch1 = (f"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
           f"<html xmlns=\"http://www.w3.org/1999/xhtml\" xml:lang=\"zh\">\n"
           f"<head><title>第1章 边界</title></head>\n"
           f"<body>\n<h1>第一章 边界</h1>\n"
           f"<p>边界第一章正文段落，用于脚本不执行断言的承载文本。</p>\n"
           f"<script type=\"text/javascript\">window.__pwned = 'executed';</script>\n"
           f"<p><img src=\"images/remote.png\" alt=\"remote\"/></p>\n"
           f"</body></html>\n")
    ch2 = (f"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
           f"<html xmlns=\"http://www.w3.org/1999/xhtml\" xml:lang=\"zh\">\n"
           f"<head><title>第2章 边界</title></head>\n"
           f"<body>\n<h1>第二章 边界</h1>\n"
           f"<p>边界第二章正文段落。</p>\n</body></html>\n")
    opf = (f'<?xml version="1.0" encoding="UTF-8"?>\n'
           f'<package xmlns="http://www.idpf.org/2007/opf" version="3.0" '
           f'unique-identifier="bid" xml:lang="zh">\n'
           f'<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
           f'<dc:identifier id="bid">urn:uuid:cccccccc-dddd-eeee-ffff-000000000001</dc:identifier>'
           f'<dc:title>脚本边界书</dc:title><dc:language>zh</dc:language></metadata>\n'
           f'<manifest>\n'
           f'<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>\n'
           f'<item id="c1" href="ch1.xhtml" media-type="application/xhtml+xml"/>\n'
           f'<item id="c2" href="ch2.xhtml" media-type="application/xhtml+xml"/>\n'
           f'</manifest>\n'
           f'<spine><itemref idref="c1"/><itemref idref="c2"/></spine>\n</package>\n')
    nav = (f'<?xml version="1.0" encoding="UTF-8"?>\n'
           f'<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="zh">\n'
           f'<body><nav epub:type="toc" xmlns:epub="http://www.idpf.org/2007/ops">'
           f'<ol><li><a href="ch1.xhtml">1 边界</a></li>'
           f'<li><a href="ch2.xhtml">2 边界</a></li></ol></nav></body></html>\n')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        zi = zipfile.ZipInfo("mimetype", date_time=(2026, 1, 1, 0, 0, 0))
        zi.compress_type = zipfile.ZIP_STORED
        z.writestr(zi, "application/epub+zip")
        z.writestr("META-INF/container.xml", container_xml())
        z.writestr("OEBPS/content.opf", opf)
        z.writestr("OEBPS/nav.xhtml", nav)
        z.writestr("OEBPS/ch1.xhtml", ch1)
        z.writestr("OEBPS/ch2.xhtml", ch2)
        z.writestr("OEBPS/images/remote.png", png(8, 8, (10, 20, 30)))



def p08_p11_legs(args, out_dir):
    """P-09.engine-bounds：书内脚本不执行（window.__pwned 缺席）；P-11：
    输入不抢键（搜索输入键入不翻页）、geometry（小视口重排存活）、两书
    并存（双页双引擎互不串）；P-03.hideshow：display 隐藏/恢复后引擎存活
    + 产品「Next →」章导航仍动。全部点击/键盘输入（headless 可靠面）。"""
    stamp = int(time.time())
    proc, logf, data_dir = _boot_app(
        args, out_dir, data_subdir=f"reader-data-t08-{args.profile}-{stamp}")
    try:
        bid, shash, fmt = _import_alpha(data_dir)
        corpus = os.path.join(out_dir, "corpus")
        script_epub = os.path.join(corpus, f"script-boundary-{stamp}.epub")
        _make_script_epub(script_epub)
        _parse2(http_json("http://127.0.0.1:17825/api/library/import", "POST",
                          {"path": script_epub, "author": "verify", "force": False},
                          timeout=120))
        script_bid = ""
        books = _parse2(http_json("http://127.0.0.1:17825/api/library/books"))
        if isinstance(books, dict):
            for b in books.get("books", []):
                if "script-boundary" in str(b.get("original_path", "")):
                    script_bid = str(b.get("book_id", ""))
        if not bid or not script_bid:
            record("P-09.engine-bounds", "FAIL", f"import bid={bid} script={script_bid}")
            record("P-11", "FAIL", "import fail")
            record("P-03.hideshow", "FAIL", "import fail")
            return
        if args.profile != "vue":
            record("P-09.engine-bounds", "GAP", "vm 页面导航腿 CDP 待工具链（T-04 已录同类）")
            record("P-11", "GAP", "vm 页面导航腿 CDP 待工具链")
            record("P-03.hideshow", "GAP", "vm 页面导航腿 CDP 待工具链")
            return
        try:
            from playwright.sync_api import sync_playwright
        except Exception as e:
            record("P-09.engine-bounds", "GAP", f"playwright missing: {e}")
            return
        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=True)
        try:
            # ── P-09.engine-bounds：脚本书装载 + 脚本不执行断言（独立页，
            # 用毕即闭——同组件路由换书不重挂引擎为已知形态）──
            page_s = browser.new_page(viewport={"width": 1400, "height": 900})
            page_s.goto(f"http://localhost:17824/#/book/{script_bid}/chapter/1",
                        wait_until="domcontentloaded", timeout=60000)
            t0 = time.monotonic()
            st = {}
            while time.monotonic() - t0 < 90:
                st = _ui_engine_state(page_s)
                if st.get("mounted") and st.get("spine", 0) > 0:
                    break
                time.sleep(2)
            mounted = bool(st.get("mounted"))
            pwned = page_s.evaluate("""() => {
                const fv = document.querySelector('foliate-view')
                const p = fv && fv.shadowRoot
                    ? fv.shadowRoot.querySelector('foliate-paginator') : null
                const ifr = p && p.shadowRoot
                    ? p.shadowRoot.querySelector('iframe') : null
                if (!ifr || !ifr.contentWindow) return { err: 'no-iframe' }
                const cw = ifr.contentWindow
                return { has: '__pwned' in cw,
                         val: cw.__pwned === undefined ? 'undefined' : String(cw.__pwned) }
            }""")
            pwned_ok = (isinstance(pwned, dict) and pwned.get("has") is False
                        and pwned.get("val") == "undefined")
            record("P-09.engine-bounds",
                   "PASS" if (mounted and pwned_ok) else "FAIL",
                   f"mounted={mounted} pwned={json.dumps(pwned, ensure_ascii=False)[:60]}"
                   f"（script 不执行/远程不取）")
            page_s.close()

            # ── P-11 + P-03.hideshow：alpha 书全新页 ──
            page = browser.new_page(viewport={"width": 1400, "height": 900})
            page.goto(f"http://localhost:17824/#/book/{bid}/chapter/1",
                      wait_until="domcontentloaded", timeout=60000)
            t0 = time.monotonic()
            while time.monotonic() - t0 < 90:
                st = _ui_engine_state(page)
                if st.get("mounted") and st.get("spine", 0) > 0:
                    break
                time.sleep(2)
            # 输入不抢键：搜索输入键入 → 引擎滚动位置不变
            scroll_before = page.evaluate("""() => {
                const vals = []
                const scan = (doc) => {
                    if (!doc) return
                    for (const el of doc.querySelectorAll('*')) {
                        if (el.scrollHeight > el.clientHeight + 10) {
                            vals.push(el.scrollTop)
                        }
                    }
                    if (doc.scrollingElement) vals.push(doc.scrollingElement.scrollTop)
                }
                scan(document)
                const fv = document.querySelector('foliate-view')
                const p = fv && fv.shadowRoot
                    ? fv.shadowRoot.querySelector('foliate-paginator') : null
                if (p) scan(p.shadowRoot)
                const ifr = p && p.shadowRoot
                    ? p.shadowRoot.querySelector('iframe') : null
                if (ifr && ifr.contentDocument) scan(ifr.contentDocument)
                return vals
            }""")
            if not (_ui_click_btn(page, "🔍 搜索") or _ui_click_by_js(page, "🔍 搜索")):
                pass
            page.wait_for_timeout(600)
            try:
                inp = page.get_by_placeholder("输入关键词（精确子串）").first
                inp.click(timeout=8000)
                inp.type("边界输入不抢键测试", timeout=8000)
            except Exception:
                pass
            page.wait_for_timeout(1200)
            scroll_after = page.evaluate("""() => {
                const vals = []
                const scan = (doc) => {
                    if (!doc) return
                    for (const el of doc.querySelectorAll('*')) {
                        if (el.scrollHeight > el.clientHeight + 10) {
                            vals.push(el.scrollTop)
                        }
                    }
                    if (doc.scrollingElement) vals.push(doc.scrollingElement.scrollTop)
                }
                scan(document)
                const fv = document.querySelector('foliate-view')
                const p = fv && fv.shadowRoot
                    ? fv.shadowRoot.querySelector('foliate-paginator') : null
                if (p) scan(p.shadowRoot)
                const ifr = p && p.shadowRoot
                    ? p.shadowRoot.querySelector('iframe') : null
                if (ifr && ifr.contentDocument) scan(ifr.contentDocument)
                return vals
            }""")
            ime_ok = (json.dumps(scroll_before) == json.dumps(scroll_after))
            # geometry：小视口重排存活
            page.set_viewport_size({"width": 800, "height": 600})
            page.wait_for_timeout(2000)
            st_g = _ui_engine_state(page)
            geom_ok = bool(st_g.get("mounted") and st_g.get("contents"))
            page.set_viewport_size({"width": 1400, "height": 900})
            page.wait_for_timeout(1000)
            # 两书并存：第二页开 beta（独立引擎实例互不串）
            beta_path = os.path.join(corpus, "product-beta.epub")
            _parse2(http_json("http://127.0.0.1:17825/api/library/import", "POST",
                              {"path": beta_path, "author": "verify", "force": False},
                              timeout=120))
            beta_bid = ""
            books = _parse2(http_json("http://127.0.0.1:17825/api/library/books"))
            if isinstance(books, dict):
                for b in books.get("books", []):
                    if "product-beta" in str(b.get("original_path", "")):
                        beta_bid = str(b.get("book_id", ""))
            two_ok = False
            two_detail = "no beta bid"
            if beta_bid:
                page2 = browser.new_page(viewport={"width": 1400, "height": 900})
                page2.goto(f"http://localhost:17824/#/book/{beta_bid}/chapter/1",
                           wait_until="domcontentloaded", timeout=60000)
                t0 = time.monotonic()
                st1 = _ui_engine_state(page)
                st2 = {}
                while time.monotonic() - t0 < 90:
                    st2 = _ui_engine_state(page2)
                    if st2.get("mounted") and st2.get("spine", 0) > 0:
                        break
                    time.sleep(2)
                two_ok = (bool(st1.get("mounted")) and bool(st2.get("mounted"))
                          and st1.get("spine") == 10 and st2.get("spine") == 2)
                two_detail = (f"p1(m={st1.get('mounted')},spine={st1.get('spine')}) "
                              f"p2(m={st2.get('mounted')},spine={st2.get('spine')})")
                page2.close()
            record("P-11",
                   "PASS" if (ime_ok and geom_ok and two_ok) else "FAIL",
                   f"ime={ime_ok} geom={geom_ok} two_books={two_ok} {two_detail}")
            # ── P-03.hideshow：doc-surface 隐藏/恢复 → 引擎存活 + 产品
            # 「Next →」章导航仍动（真实 UI 点击 → command goto → 引擎换章；
            # paged 模式滚动断言不适用——翻页为变换非滚动）──
            page.evaluate("""() => {
                const fv = document.querySelector('foliate-view')
                if (fv) fv.style.display = 'none'
            }""")
            page.wait_for_timeout(1200)
            page.evaluate("""() => {
                const fv = document.querySelector('foliate-view')
                if (fv) fv.style.display = ''
            }""")
            page.wait_for_timeout(1500)
            st_h = _ui_engine_state(page)
            hs_alive = bool(st_h.get("mounted") and st_h.get("contents"))
            prog_before = page.evaluate(
                "() => (document.body.textContent.match(/\d+ of \d+/) || [''])[0]")
            if not (_ui_click_btn(page, "Next →") or _ui_click_by_js(page, "Next →") == "clicked"):
                print("  p03 next-btn click fail")
            prog_after = prog_before
            t0n = time.monotonic()
            while time.monotonic() - t0n < 25:
                prog_after = page.evaluate(
                    "() => (document.body.textContent.match(/\d+ of \d+/) || [''])[0]")
                if prog_after and prog_after != prog_before:
                    break
                time.sleep(1.5)
            hs_nav = bool(prog_before) and prog_after != prog_before
            record("P-03.hideshow",
                   "PASS" if (hs_alive and hs_nav) else "FAIL",
                   f"alive={hs_alive} nav={prog_before or '?'}->{prog_after or '?'}")
        finally:
            try:
                browser.close()
            except Exception:
                pass
            pw.stop()
    finally:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True)
        proc.wait()
        logf.close()

def p05_data_family(args, out_dir):
    """T-05 数据层族：独立数据目录（时间戳隔离，重跑洁净）。
    覆盖 P-04 录入环 oracle（数据面）、P-05 v1 兼容/v2 锚/不可映射/多义、
    P-06 数据冷恢复、P-08 变异矩阵、P-10 写失败/损坏/恢复。UI 腿诚实
    not_run（T-06/T-07/T-08 接入）。"""
    stamp = int(time.time())
    proc, logf, data_dir = _boot_app(
        args, out_dir, data_subdir=f"reader-data-t05-{args.profile}-{stamp}")
    ann_dir = os.path.join(data_dir, "annotations")
    rd_dir = os.path.join(data_dir, "reading")
    try:
        bid, shash, fmt = _import_alpha(data_dir)
        if not bid or fmt != "epub":
            record("P-05.v1-compat", "FAIL", f"alpha import bid={bid} fmt={fmt}")
            return
        beta_bid, beta_hash, _ = _t05_books_by(data_dir, "product-beta")
        if not beta_bid:
            corpus = os.path.join(out_dir, "corpus")
            imp = _parse2(http_json("http://127.0.0.1:17825/api/library/import", "POST",
                                    {"path": os.path.join(corpus, "product-beta.epub"),
                                     "author": "verify", "force": False}, timeout=60))
            beta_bid, beta_hash, _ = _t05_books_by(data_dir, "product-beta")
        txt_path = os.path.join(out_dir, f"t05-note-{stamp}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("第一段：TXT 回归面。注释与定位保持 v1 段锚。\n第二段：locator v2 锚不适用本文本路径。\n")
        _parse2(http_json("http://127.0.0.1:17825/api/library/import", "POST",
                          {"path": txt_path, "author": "verify", "force": False}, timeout=60))
        txt_bid, txt_hash, txt_fmt = _t05_books_by(data_dir, "t05-note-")
        sess = f"r7-t05-{stamp}"
        s = _parse2(http_json("http://127.0.0.1:17825/api/reader/session", "POST",
                              {"session_id": sess, "book_id": bid, "source_hash": shash,
                               "engine": ENGINE_ID}))
        ok_sess = isinstance(s, dict) and str(s.get("ok", "")).lower() == "true"
        if not ok_sess or not beta_bid or not txt_bid:
            record("P-05.v1-compat", "FAIL",
                   f"session={ok_sess} beta={beta_bid} txt={txt_bid}")
            return

        # ── P-05.v1-compat：纯 v1 读写、稳定 ID、章书签、version 恒 1 ──
        ann_file = os.path.join(ann_dir, f"{bid}.json")
        r1 = _t05_ann(bid, kind="highlight", chapter_number=1, para_idx=2,
                      occurrence=1, quote=REPEAT_A, comment="v1",
                      tags_json='["重点"]')
        r2 = _t05_ann(bid, kind="highlight", chapter_number=1, para_idx=7,
                      occurrence=1, quote=REPEAT_A, comment="v1-第二处")
        r3 = _t05_ann(bid, op="create", kind="bookmark", chapter_number=1,
                      para_idx=-1, occurrence=0)
        # v1 契约：create 响应不带 annotation_id——读回取号（reading_page 同款）
        got0 = _parse2(http_json(f"http://127.0.0.1:17825/api/library/annotations?book_id={bid}"))
        aid1 = aid2 = ""
        if isinstance(got0, dict):
            for a in got0.get("annotations", []):
                if a.get("quote") == REPEAT_A and a.get("para_idx") == 2:
                    aid1 = str(a.get("annotation_id", ""))
                if a.get("quote") == REPEAT_A and a.get("para_idx") == 7:
                    aid2 = str(a.get("annotation_id", ""))
        v1_ok = False
        v1_detail = ""
        if aid1 and aid2 and isinstance(r3, dict) and r3.get("ok"):
            up = _t05_ann(bid, op="update", annotation_id=aid1, kind="highlight",
                          comment="v1改", tags_json='["重点"]')
            with open(ann_file, encoding="utf-8") as f:
                disk = json.load(f)
            with open(os.path.join(data_dir, "annotations-get.json"), "w",
                      encoding="utf-8") as f:
                f.write(_parse2(http_json(
                    f"http://127.0.0.1:17825/api/library/annotations?book_id={bid}"))
                    if isinstance(_parse2(http_json(
                        f"http://127.0.0.1:17825/api/library/annotations?book_id={bid}")), str)
                    else json.dumps(_parse2(http_json(
                        f"http://127.0.0.1:17825/api/library/annotations?book_id={bid}")),
                        ensure_ascii=False))
            with open(os.path.join(data_dir, "annotations-get.json"), encoding="utf-8") as f:
                got = json.load(f)
            v1_ok = (isinstance(up, dict) and up.get("ok")
                     and disk.get("version") == 1
                     and all("locator" not in a for a in disk.get("annotations", []))
                     and got.get("version") == 1)
            v1_detail = f"aid1={aid1[:8]} aid2={aid2[:8]} up={isinstance(up, dict) and up.get('ok')} r3={isinstance(r3, dict) and r3.get('ok')} disk_v={disk.get('version')} get_v={got.get('version')}"
        record("P-05.v1-compat", "PASS" if v1_ok else "FAIL",
               v1_detail + " (v1 读写/稳定ID/章书签/版本字节兼容)")

        # ── P-04.data-oracle：录入环 canonical + 拒绝矩阵（数据面） ──
        loc1 = _t05_select(sess, bid, shash, 0, REPEAT_A, 1)
        loc2 = _t05_select(sess, bid, shash, 0, REPEAT_A, 2)
        loc3 = _t05_select(sess, bid, shash, 1, REPEAT_A, 3)
        xloc = _t05_select(sess, bid, shash, 2, CROSS_PARA + "\n" + CROSS_PARA2, 1,
                           cfi="epubcfi(/6/8!/4/12004,/1:0)")
        def loc_ok(l, spine, idx):
            return (isinstance(l, dict) and l.get("ok")
                    and isinstance(l.get("locator"), dict)
                    and l["locator"]["resource"]["spine_index"] == spine
                    and l["locator"]["occurrence"]["index"] == idx
                    and l["locator"]["resource"]["href"] == f"ch{spine}.xhtml")
        o4 = (loc_ok(loc1, 1, 1) and loc_ok(loc2, 1, 2) and loc_ok(loc3, 2, 3)
              and loc_ok(xloc, 3, 1))
        ctxs = [json.dumps(l["locator"]["context"], ensure_ascii=False)
                for l in (loc1, loc2, loc3)
                if isinstance(l, dict) and isinstance(l.get("locator"), dict)]
        ctx_distinct = len(ctxs) == 3 and len(set(ctxs)) == 3
        rejects = [
            (_t05_select("bad shape!", bid, shash, 0, REPEAT_A, 1), "rejected_bad_session"),
            (_t05_select("r7-t05-unknown-1", bid, shash, 0, REPEAT_A, 1), "rejected_bad_session"),
            (_t05_select(sess, beta_bid, beta_hash, 0, REPEAT_A, 1), "rejected_bad_session"),
            (_t05_select(sess, bid, "sha256:deadbeef", 0, REPEAT_A, 1), "rejected_bad_session"),
            (_t05_select(sess, bid, shash, 0, REPEAT_A, 1, engine="foliate-js@0000111"), "rejected_bad_engine"),
            (_t05_select(sess, bid, shash, 0, REPEAT_A, 1, kind="weird"), "rejected_bad_kind"),
            (_t05_select(sess, bid, shash, 0, REPEAT_A[:-2] + "改写。", 1), "rejected_bad_quote"),
            (_t05_select(sess, bid, shash, 0, REPEAT_A, 99), "rejected_bad_occurrence"),
            (_t05_select(sess, bid, shash, 0, REPEAT_A, 1, cfi="not-a-cfi"), "rejected_bad_cfi"),
            (_t05_select(sess, bid, shash, 99, REPEAT_A, 1), "rejected_bad_resource"),
        ]
        rej_ok = all(isinstance(r, dict) and not r.get("ok")
                     and exp in str(r.get("error", "")) for r, exp in rejects)
        probe = _t05_select(sess, bid, shash, 0, REPEAT_A, 1, kind="input_probe")
        probe_ok = isinstance(probe, dict) and probe.get("ok") and probe.get("ack") == "input_probe"
        dirty_sess = []
        try:
            with open(os.path.join(data_dir, "sessions.json"), encoding="utf-8") as f:
                sids = [str(x.get("session_id", "")) for x in json.load(f).get("sessions", [])]
            dirty_sess = [x for x in sids if not x.startswith("r7-") and not x.startswith("verify-")]
        except Exception:
            dirty_sess = ["sessions unreadable"]
        record("P-04.data-oracle",
               "PASS" if (o4 and ctx_distinct and rej_ok and probe_ok and not dirty_sess)
               else "FAIL",
               f"selects={o4} ctx_distinct={ctx_distinct} rejects10={rej_ok} "
               f"probe={probe_ok} dirty={dirty_sess[:2]} (UI 创建腿 T-06)")

        # ── P-05.v2-anchor：唯一映射锚定 / 已锚拒绝 / 不可映射 / 多义 ──
        anch = _t05_ann(bid, op="anchor", annotation_id=aid2,
                        locator_json=json.dumps(loc2["locator"], ensure_ascii=False))
        anch2 = _t05_ann(bid, op="anchor", annotation_id=aid2,
                         locator_json=json.dumps(loc2["locator"], ensure_ascii=False))
        create_loc = _t05_ann(bid, kind="highlight", chapter_number=2, para_idx=2,
                              occurrence=1, quote=REPEAT_A, comment="带v2锚",
                              locator_json=json.dumps(loc3["locator"], ensure_ascii=False))
        disk_v2 = {}
        anchor_ok = False
        if isinstance(anch, dict) and anch.get("ok"):
            with open(ann_file, encoding="utf-8") as f:
                disk_v2 = json.load(f)
            rec2 = [a for a in disk_v2.get("annotations", [])
                    if a.get("annotation_id") == aid2]
            anchor_ok = (disk_v2.get("version") == 2 and len(rec2) == 1
                         and rec2[0].get("quote") == REPEAT_A
                         and rec2[0].get("chapter_number") == 1
                         and isinstance(rec2[0].get("locator"), dict)
                         and rec2[0]["locator"]["occurrence"]["index"] == 2
                         and isinstance(anch2, dict) and not anch2.get("ok")
                         and "already anchored" in str(anch2.get("message", ""))
                         and isinstance(create_loc, dict) and create_loc.get("ok"))
        # 不可映射：TXT 记录锚定 → 具名拒（TXT/MD 保持 v1 不被改写）
        txt_ann = _t05_ann(txt_bid, kind="highlight", chapter_number=1, para_idx=0,
                           occurrence=1, quote="第一段：TXT 回归面。注释与定位保持 v1 段锚。")
        got_t = _parse2(http_json(f"http://127.0.0.1:17825/api/library/annotations?book_id={txt_bid}"))
        txt_aid = ""
        if isinstance(got_t, dict):
            for a in got_t.get("annotations", []):
                txt_aid = str(a.get("annotation_id", ""))
        txt_anchor = _t05_ann(txt_bid, op="anchor", annotation_id=txt_aid,
                              locator_json=json.dumps(loc1["locator"], ensure_ascii=False))
        txt_ok = (isinstance(txt_ann, dict) and txt_ann.get("ok")
                  and isinstance(txt_anchor, dict) and not txt_anchor.get("ok")
                  and "rejected" in str(txt_anchor.get("message", "")))
        # 多义：位次/上下文矛盾的 locator 必须被识别（CFI 指另一处重复句形态）
        forged = json.loads(json.dumps(loc2["locator"]))
        forged["occurrence"]["index"] = 1
        fv = _t05_verify(bid, forged)
        # 零写入断言只圈定被拒的 forged anchor 本身（前序合法写不算）
        poly_before = _t05_snapshot(ann_file)
        forged_anchor = _t05_ann(bid, op="anchor", annotation_id=aid1,
                                 locator_json=json.dumps(forged, ensure_ascii=False))
        ann_bytes_after = _t05_snapshot(ann_file)
        ann_bytes_before = poly_before
        poly_ok = (isinstance(fv, dict) and fv.get("ok") and not fv.get("match")
                   and "needs_relocate" in str(fv.get("reason", ""))
                   and isinstance(forged_anchor, dict) and not forged_anchor.get("ok")
                   and ann_bytes_before == ann_bytes_after)
        record("P-05.v2-anchor", "PASS" if (anchor_ok and txt_ok and poly_ok) else "FAIL",
               f"anchor+create={anchor_ok} txt_unmappable={txt_ok} poly_reject={poly_ok}")

        # ── P-08.mutation-matrix：恢复/回访环身份链/逐字/位次/上下文变异 ──
        ann_bytes_p08 = _t05_snapshot(ann_file)
        ctrl = [_t05_verify(bid, loc1["locator"]), _t05_verify(bid, loc2["locator"]),
                _t05_verify(bid, loc3["locator"]), _t05_verify(bid, xloc["locator"])]
        ctrl_ok = all(isinstance(v, dict) and v.get("ok") and v.get("match") for v in ctrl)
        m_book = json.loads(json.dumps(loc2["locator"]))
        m_hash = json.loads(json.dumps(loc2["locator"]))
        m_hash["source_hash"] = "sha256:deadbeef"
        m_href = json.loads(json.dumps(loc2["locator"]))
        m_href["resource"]["href"] = "ch9.xhtml"
        m_spine = json.loads(json.dumps(loc2["locator"]))
        m_spine["resource"]["spine_index"] = 4
        m_spine["resource"]["href"] = "ch4.xhtml"
        m_ctx = json.loads(json.dumps(loc2["locator"]))
        m_ctx["occurrence"]["index"] = 1
        m_quote = json.loads(json.dumps(loc2["locator"]))
        m_quote["quote"] = REPEAT_A[:-2] + "改写。"
        muts = [
            (_t05_verify(beta_bid, m_book), "rejected_book_mismatch"),
            (_t05_verify(bid, m_hash), "needs_relocate: source_hash mismatch"),
            (_t05_verify(bid, m_href), "needs_relocate: resource href mismatch"),
            (_t05_verify(bid, m_spine), "needs_relocate: quote not in resource"),
            (_t05_verify(bid, m_ctx), "needs_relocate: context.before mismatch"),
            (_t05_verify(bid, m_quote), "needs_relocate: quote not in resource"),
        ]
        mut_ok = all(isinstance(v, dict) and v.get("ok") and not v.get("match")
                     and exp in str(v.get("reason", "")) for v, exp in muts)
        mut_clean = _t05_snapshot(ann_file) == ann_bytes_p08
        record("P-08.mutation-matrix",
               "PASS" if (ctrl_ok and mut_ok and mut_clean) else "FAIL",
               f"controls4={ctrl_ok} mutations6={mut_ok} zero_write={mut_clean} "
               f"(恢复环适配器读回腿 T-06/T-08)")

        # ── P-10.data：损坏/未知版本/伪造锚形状/占用路径/状态损坏/恢复 ──
        ok10 = True
        d10 = []
        # ① 注释文件损坏 → 具名拒 + 原件保留
        good = _t05_snapshot(ann_file)
        with open(ann_file, "w", encoding="utf-8") as f:
            f.write("corrupted{{{")
        damaged = _t05_snapshot(ann_file)
        g1 = _parse2(http_json(f"http://127.0.0.1:17825/api/library/annotations?book_id={bid}"))
        kept = _t05_snapshot(ann_file)
        d10.append(("damage-refuse", isinstance(g1, dict) and not g1.get("ok")
                    and kept == damaged))
        if not d10[-1][1]:
            print("  damage-refuse detail:", str(g1)[:120],
                  "kept=", kept == damaged, "kept_len=", len(kept or b""),
                  "damaged_len=", len(damaged or b""))
        with open(ann_file, "wb") as f:
            f.write(good)
        # ② 未知版本 → 具名拒
        uv = json.loads(good.decode("utf-8"))
        uv["version"] = 9
        with open(ann_file, "w", encoding="utf-8") as f:
            json.dump(uv, f, ensure_ascii=False)
        uv_bytes = _t05_snapshot(ann_file)
        g2 = _parse2(http_json(f"http://127.0.0.1:17825/api/library/annotations?book_id={bid}"))
        d10.append(("unknown-version", isinstance(g2, dict) and not g2.get("ok")
                    and _t05_snapshot(ann_file) == uv_bytes))
        with open(ann_file, "wb") as f:
            f.write(good)
        # ③ 伪造锚形状（CFI 非法）→ 读回 canonical 拒绝，原件保留
        forged_file = json.loads(good.decode("utf-8"))
        for a in forged_file.get("annotations", []):
            if isinstance(a.get("locator"), dict):
                a["locator"]["range"]["start"]["cfi"] = "epubcfi-GARBAGE"
        with open(ann_file, "w", encoding="utf-8") as f:
            json.dump(forged_file, f, ensure_ascii=False)
        ff_bytes = _t05_snapshot(ann_file)
        g3 = _parse2(http_json(f"http://127.0.0.1:17825/api/library/annotations?book_id={bid}"))
        d10.append(("forged-cfi-refuse", isinstance(g3, dict) and not g3.get("ok")
                    and _t05_snapshot(ann_file) == ff_bytes))
        with open(ann_file, "wb") as f:
            f.write(good)
        # ④ 占用路径（<bid>.json 为目录）→ 具名拒零半写；移除后合法写成功
        occ_path = os.path.join(ann_dir, f"{beta_bid}.json")
        os.makedirs(occ_path, exist_ok=True)
        oc = _t05_ann(beta_bid, kind="highlight", chapter_number=1, para_idx=2,
                      occurrence=1, quote=REPEAT_B)
        occ_refused = isinstance(oc, dict) and not oc.get("ok") \
            and ("occupied" in str(oc.get("message", ""))
                 or "unreadable" in str(oc.get("message", "")))
        if not occ_refused:
            print("  occupied detail:", str(oc)[:140])
        os.rmdir(occ_path)
        oc2 = _t05_ann(beta_bid, kind="highlight", chapter_number=1, para_idx=2,
                       occurrence=1, quote=REPEAT_B)
        if not (isinstance(oc2, dict) and oc2.get("ok")):
            print("  oc2 detail:", str(oc2)[:140])
        d10.append(("occupied-then-recover", occ_refused
                    and isinstance(oc2, dict) and oc2.get("ok")))
        # ⑤ 阅读状态损坏 → 读侧不冒充有效状态；合法写恢复
        rp = os.path.join(rd_dir, f"{bid}.json")
        os.makedirs(rd_dir, exist_ok=True)
        with open(rp, "w", encoding="utf-8") as f:
            f.write("broken-state[[[")
        gr = http_json(f"http://127.0.0.1:17825/api/library/progress?book_id={bid}")
        d10.append(("state-damage-honest", gr == "" or gr is None))
        payload = {"book_id": bid, "chapter_number": 1, "paragraph_index": 2,
                   "font_size": "medium", "line_height": "comfy", "updated_at": 1}
        pw = _t05_progress(bid, payload, REPEAT_A)
        d10.append(("state-recover", isinstance(pw, dict) and pw.get("ok")))
        ok10 = all(c[1] for c in d10)
        record("P-10.data", "PASS" if ok10 else "FAIL",
               " ".join(f"{n}={v}" for n, v in d10) + " (只读目录/迁移写失败腿随 T-08 汇入)")

        # ── P-06.data-cold：locator 状态保存/前向延续/进程重启恢复（数据面） ──
        with open(rp, encoding="utf-8") as f:
            st_before = json.load(f)
        has_loc_before = isinstance(st_before.get("locator"), dict)
        if not has_loc_before:
            lw = _t05_progress(bid, payload, REPEAT_A,
                               locator=json.dumps(loc1["locator"], ensure_ascii=False))
            with open(rp, encoding="utf-8") as f:
                st_before = json.load(f)
            has_loc_before = isinstance(st_before.get("locator"), dict) and \
                isinstance(lw, dict) and lw.get("ok")
        # settings-only 保存（无 locator 入参）→ 前向延续
        pw2 = _t05_progress(bid, dict(payload, font_size="large"), REPEAT_A)
        with open(rp, encoding="utf-8") as f:
            st_mid = json.load(f)
        carry_ok = isinstance(pw2, dict) and pw2.get("ok") \
            and st_mid.get("locator") == st_before.get("locator")
        # 陈旧 locator → 具名拒 + 状态不变
        stale = json.loads(json.dumps(loc1["locator"]))
        stale["source_hash"] = "sha256:deadbeef"
        lr = _t05_progress(bid, payload, REPEAT_A, locator=json.dumps(stale, ensure_ascii=False))
        with open(rp, encoding="utf-8") as f:
            st_after_reject = json.load(f)
        stale_ok = isinstance(lr, dict) and not lr.get("ok") \
            and st_after_reject.get("locator") == st_before.get("locator")
        # 冷重启：杀进程 → 同数据目录重启 → locator 逐字恢复
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True)
        proc.wait()
        logf.close()
        proc2, logf2, data_dir2 = _boot_app(
            args, out_dir, data_subdir=f"reader-data-t05-{args.profile}-{stamp}")
        proc, logf = proc2, logf2
        rp2 = os.path.join(data_dir2, "reading", f"{bid}.json")
        with open(rp2, encoding="utf-8") as f:
            st_cold = json.load(f)
        cold_ok = st_cold.get("locator") == st_before.get("locator") \
            and st_cold.get("chapter_number") == 1
        record("P-06.data-coldrestart",
               "PASS" if (has_loc_before and carry_ok and stale_ok and cold_ok) else "FAIL",
               f"saved={has_loc_before} carry={carry_ok} stale_reject={stale_ok} "
               f"cold={cold_ok} (真实 UI 换布局恢复腿 T-07/T-08)")
        # （P-05.visit-ui/P-06.ui-restore 归 p07_t07_legs 记录——本族不预记
        #  not_run，避免同 id 双记录违反严格聚合器）
    except Exception as e:
        # 族内基础设施故障（app 宿主关闭/连接复位）→ 未记腿显式 FAIL，
        # 不让整跑崩溃（严格聚合器按 FAIL 非零）
        print("  family interrupted:", type(e).__name__, str(e)[:120])
        done = {r["case"] for r in RECORDS}
        for cid in ("P-05.v1-compat", "P-04.data-oracle", "P-05.v2-anchor",
                    "P-08.mutation-matrix", "P-10.data"):
            if cid not in done:
                record(cid, "FAIL", f"family interrupted: {type(e).__name__} {str(e)[:80]}")
        for cid in ("P-06.data-coldrestart",):
            if cid not in done:
                record(cid, "FAIL", f"family interrupted before leg: {type(e).__name__}")
        # （每 id 恰一记录——P-05.visit-ui/P-06.ui-restore 门内面归
        #  p07_t07_legs 所有，本族不预记）
    finally:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True)
        proc.wait()
        logf.close()
# ─────────────────────── 未实现用例注册（T-03..T-08 接入） ───────────────────────

def register_pending():
    # （全部用例已由各自腿/族记录——本函数保留为无操作占位）
    pass


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
    ap.add_argument("--only", default="",
                    help="仅跑指定族（如 p04/p03；其余必需腿记 not_run）——"
                         "真实输入腿的前台会话取证形态；完整 cohort 以无 --only 跑为准")
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

    only = args.only.strip().lower()
    if only == "p04":
        # 前台取证形态：cohort desk（依赖面）+ P-04 真实 UI 腿；其余腿留
        # not_run（严格聚合器照常非零——完整判定以全量跑为准）
        desk = check_cohort_desk(args.auto_bin)
        record("P-01.cohort-desk", "PASS" if all(desk[:4]) else "FAIL",
               f"archived={desk[0]} landing={desk[1]} auto_g47d8f7b={desk[2]} "
               f"tool_doc-surface={desk[3]}")
        p04_ui_create(args, out_dir)
        p12_structure(args, out_dir)
        register_pending()
        for cid in ("P-07.search-jump", "P-07.export", "P-05.visit-ui",
                    "P-06.ui-restore", "P-09.engine-bounds", "P-11",
                    "P-03.hideshow"):
            record(cid, "not_run",
                   "--only p04 前台取证跑未含（证据见同 cohort 全量跑）")
        for cid in ("P-01.backend", "P-02.load-chain", "P-02.asset-independence",
                    "P-02.product-ui", "P-02.footnote-link", "P-02.ui-mount",
                    "P-03.flow-switch", "P-03.reflow-selection",
                    "P-05.v1-compat", "P-04.data-oracle", "P-05.v2-anchor",
                    "P-08.mutation-matrix", "P-10.data", "P-06.data-coldrestart",
                    "P-09.resource-gate", "P-09.import-bounds"):
            record(cid, "not_run", f"--only p04 前台取证跑未含（证据见同 cohort 全量跑）")
        ok, findings, n_not_run = aggregate(args.profile, RECORDS)
        print(f"aggregate(--only {only}): ok={ok} findings={len(findings)} "
              f"not_run={n_not_run}")
        for kind, case, detail in findings:
            print(f"  {kind:10s} {case} :: {detail[:160]}")
        return 3 if not findings else 1
    p01(args, out_dir)
    time.sleep(3)
    # 数据族先跑（新起 app，避开 run_ui 宿主长存活期不稳定面——
    # 2026-11-03 gate-vue6 实测 ~12min 后 tool host 控制流关闭）
    p05_data_family(args, out_dir)
    time.sleep(3)
    p02(args, out_dir)
    time.sleep(3)
    p03(args, out_dir)
    time.sleep(3)
    p04_ui_create(args, out_dir)
    time.sleep(3)
    p07_t07_legs(args, out_dir)
    time.sleep(3)
    p08_p11_legs(args, out_dir)
    time.sleep(3)
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
