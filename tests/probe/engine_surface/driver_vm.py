#!/usr/bin/env python3
# driver_vm.py — PLAN-029 原生（真实 AutoUI VM）臂表面驱动。
#
# PLAN-026 旧臂（独立 native_host.exe）退役：029 T-02 起原生表面 = 消费 app
# `auto run -r vm --no-merge`（拆分模式：AutoVM HTTP 后端 + 真实原生 iced 窗
# 口进程 auto-ui-tool.exe，cohort 经 AUTO_UI_TOOL_BIN 发现序第一键固定）。
# 链路：reader 真实导入身份 → MCP chrome 动作连接会话（NVM-03 真实消费）
# → doc-surface 子表面装载引擎 → 真实 OS SendInput 拖选（T-00 修正坐标）
# → 引擎 CFI/quote/出现序 → .at handler 核验 → sidecar 落盘 → 独立 oracle
# 与磁盘读回 → 正常/异常关闭后新进程冷恢复。不代选：选择为真实系统鼠标
# 事件；CDP 只用于翻页/只读观察与合法对照，不产生选择。
import ctypes
import ctypes.wintypes
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

from driver_vue import Instance  # 复用实例管理/导入面
from driver_vue import http as _http

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(HERE, "app")
ENGINE_REVISION = "foliate-js@3d794195"

# 目标句前缀（verify_engine_surface.REPEAT_A 同源常量；第 2 处 = ch1 para7）。
REPEAT_A_MARKER = "探针重复句甲"
# 完整目标句（verify_engine_surface.REPEAT_A 同源；oracle 逐字核验用）。
REPEAT_A = "探针重复句甲🦊：琥珀色的狐狸跃过懒狗时携带三枚星形饼干，并轻声数到十七✨，随后沿对角线穿过整段跨度以便在窄栏里真实换行。"

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# PLAN-029 T-00：驱动进程必须 per-monitor DPI-aware——此后 ClientToScreen/
# GetClientRect/GetSystemMetrics/SendInput 归一化全部处于同一物理像素坐标系。
# （026 臂未设感知：逻辑/物理坐标混用，是输入断点的成因之一，见计划 §9。）
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    user32.SetProcessDPIAware()


def _find_windows_of_pid(pid):
    hits = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(hwnd, _l):
        owner = ctypes.c_uint()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and user32.IsWindowVisible(hwnd):
            hits.append(hwnd)
        return True

    user32.EnumWindows(cb, None)
    return hits


def _probe_window_pid():
    """探针原生窗口进程 pid（pac.at title 唯一；单实例 profile）。
    双实例归属收紧（pid 树核对）随 N-07（T-06）。"""
    pid = None

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(h, _l):
        nonlocal pid
        t = ctypes.create_unicode_buffer(128)
        user32.GetWindowTextW(h, t, 128)
        if "引擎表面探针" in t.value and user32.IsWindowVisible(h):
            p = ctypes.c_uint()
            user32.GetWindowThreadProcessId(h, ctypes.byref(p))
            pid = p.value
        return True

    user32.EnumWindows(cb, None)
    return pid


def _client_origin(hwnd):
    pt = ctypes.wintypes.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    return pt.x, pt.y


def _client_size(hwnd):
    rect = ctypes.wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    return rect.right, rect.bottom


def _force_foreground(hwnd):
    """前台切换：TOPMOST → ALT 解锁 → AttachThreadInput → SetForegroundWindow
    → 仍败则最小化/恢复（恢复路径授予前台）。失败不静默——调用方回读核验。"""
    user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0053)  # HWND_TOPMOST, SWP_NOMOVE|SIZE|SHOWWINDOW
    user32.keybd_event(0x12, 0, 0, 0)                  # ALT down（解锁 SF 带）
    fg = user32.GetForegroundWindow()
    tid_fg = user32.GetWindowThreadProcessId(fg, None)
    tid_me = kernel32.GetCurrentThreadId()
    user32.AttachThreadInput(tid_me, tid_fg, True)
    user32.SetForegroundWindow(hwnd)
    user32.AttachThreadInput(tid_me, tid_fg, False)
    user32.keybd_event(0x12, 0, 2, 0)                  # ALT up
    time.sleep(0.3)
    if user32.GetForegroundWindow() != hwnd:
        try:
            ctypes.windll.user32.SwitchToThisWindow(hwnd, True)
        except Exception:
            pass
        time.sleep(0.3)
    if user32.GetForegroundWindow() != hwnd:
        user32.ShowWindow(hwnd, 6)                     # SW_MINIMIZE
        time.sleep(0.4)
        user32.ShowWindow(hwnd, 9)                     # SW_RESTORE（恢复授予前台）
        time.sleep(0.6)
    if user32.GetForegroundWindow() != hwnd:
        user32.BringWindowToTop(hwnd)
        user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0053)
        user32.SetFocus(hwnd)
    time.sleep(0.2)


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong), ("dwExtraInfo", ctypes.c_void_p)]


class _INPUT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("mi", _MOUSEINPUT)]
    _fields_ = [("type", ctypes.c_ulong), ("u", _U)]


def _abs_xy(x, y):
    # PLAN-029 T-00 实测修复：76/77 是 SM_X/YVIRTUALSCREEN（虚拟屏原点），
    # 宽高是 78/79。026 旧码用 76/77 当宽高、88/89 当原点——分母 max(1,0)=1
    # 把绝对坐标放大 ~65536 倍，输入永不落在内容上（026「原生输入 GAP」的
    # 首要根因）。
    ox = user32.GetSystemMetrics(76)   # SM_XVIRTUALSCREEN
    oy = user32.GetSystemMetrics(77)   # SM_YVIRTUALSCREEN
    sw = user32.GetSystemMetrics(78)   # SM_CXVIRTUALSCREEN
    sh = user32.GetSystemMetrics(79)   # SM_CYVIRTUALSCREEN
    nx = int((x - ox) * 65536 / max(1, sw))
    ny = int((y - oy) * 65536 / max(1, sh))
    return nx, ny


def _send_input(nx, ny, down):
    flags = 0x8000 | 0x0001          # MOUSEEVENTF_ABSOLUTE | MOVE
    mi = _MOUSEINPUT(nx, ny, 0, flags, 0, None)
    if down is True:
        mi.dwFlags |= 0x0002          # LEFTDOWN
    elif down is False:
        mi.dwFlags |= 0x0004          # LEFTUP
    inp = _INPUT(0, _INPUT._U(mi))    # INPUT_MOUSE=0
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))


def _send_mouse(x, y, down=None):
    """SendInput 绝对坐标（虚拟屏归一）——真实 OS 输入，非 JS 代选。"""
    nx, ny = _abs_xy(x, y)
    if down is None:
        _send_input(nx, ny, None)
    else:
        _send_input(nx, ny, down)


def _hit_window(x, y):
    """逐点 hit-test（物理屏幕坐标）→ (hwnd, class)。驱动输入守卫用：
    覆盖层（Windows 输入体验 CoreWindow / 残留其他窗）具名可见。"""
    pt = ctypes.wintypes.POINT(int(x), int(y))
    hw = user32.WindowFromPoint(pt)
    buf = ctypes.create_unicode_buffer(128)
    user32.GetClassNameW(hw, buf, 128)
    return hw, buf.value


# ─────────────────────── 真实 VM 实例与 MCP 面 ───────────────────────

def _mcp_call(base, name, args=None, timeout=30):
    """MCP tools/call（窗口会话 MCP 端点——NVM-03 真实 chrome 动作通道）。"""
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": name, "arguments": args or {}}}).encode()
    req = urllib.request.Request(base.rstrip("/") + "/mcp", data=body,
                                 method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _mcp_text(base, name, args=None):
    v = _mcp_call(base, name, args)
    return v["result"]["content"][0].get("text", "")


def _wait_mcp(log_path, deadline=90):
    t0 = time.monotonic()
    while time.monotonic() - t0 < deadline:
        try:
            with open(log_path, encoding="utf-8", errors="replace") as f:
                for line in f:
                    if "AutoUI MCP: listening on" in line:
                        return line.strip().rsplit(" ", 1)[-1]
        except OSError:
            pass
        time.sleep(1)
    return None


def _wait_surface_created(log_path, deadline=45):
    """doc-surface create 行 → 物理 rect (w,h,x,y)。"""
    t0 = time.monotonic()
    while time.monotonic() - t0 < deadline:
        try:
            with open(log_path, encoding="utf-8", errors="replace") as f:
                for line in f:
                    if "[doc-surface #" in line and "] create " in line:
                        m = re.search(r"phys=(\d+)x(\d+)@(\d+),(\d+)", line)
                        if m:
                            return tuple(int(g) for g in m.groups())
        except OSError:
            pass
        time.sleep(1)
    return None


class VmInstance:
    """真实 AutoUI 原生 VM 消费实例（auto run -r vm --no-merge 拆分模式）。"""

    def __init__(self, cwd, log_path, env):
        self.log_path = log_path
        self.log = open(log_path, "w", encoding="utf-8", errors="replace")
        e = dict(os.environ)
        e.update(env)
        auto = os.environ.get("PROBE_AUTO_BIN", "auto")
        self.proc = subprocess.Popen(
            [auto, "run", "-r", "vm", "--no-merge"], cwd=cwd, env=e,
            stdout=self.log, stderr=subprocess.STDOUT)

    def wait_http(self, url, deadline=90):
        t0 = time.monotonic()
        while time.monotonic() - t0 < deadline:
            if self.proc.poll() is not None:
                return False
            try:
                with urllib.request.urlopen(url, timeout=3):
                    return True
            except Exception:
                time.sleep(1.5)
        return False

    def stop(self):
        if self.proc and self.proc.poll() is None:
            subprocess.run(["taskkill", "/PID", str(self.proc.pid), "/T", "/F"],
                           capture_output=True)
            self.proc.wait()
        self.log.close()

    def kill_hard(self):
        """异常退出模拟：强杀整树（无清理路径）。"""
        if self.proc and self.proc.poll() is None:
            subprocess.run(["taskkill", "/PID", str(self.proc.pid), "/T", "/F"],
                           capture_output=True)
            self.proc.wait()


def _wait_tree(mcp_base, deadline=40):
    """等待原生树就绪（首帧构建；快照过早返回空树）。"""
    t0 = time.monotonic()
    while time.monotonic() - t0 < deadline:
        snap = _mcp_text(mcp_base, "autoui_snapshot")
        if "连接会话" in snap:
            return snap
        time.sleep(1.5)
    return _mcp_text(mcp_base, "autoui_snapshot")


def _connect_session(mcp_base, sid, log_path):
    """注册会话后经 MCP 真实 press 连接会话；返回表面物理 rect 或 None。"""
    snap = _wait_tree(mcp_base)
    mb = re.search(r'button #(\S+) "连接会话"', snap)
    if not mb:
        return None, "Connect button not in MCP tree"
    act = _mcp_text(mcp_base, "autoui_action",
                    {"element_id": mb.group(1), "action": "press"})
    if "status: ok" not in act:
        return None, "MCP press failed: " + act[:120]
    okc = False
    for _ in range(10):
        if "connected" in _mcp_text(mcp_base, "autoui_snapshot"):
            okc = True
            break
        time.sleep(1)
    if not okc:
        return None, "frontend session_state never connected"
    rect = _wait_surface_created(log_path)
    if not rect:
        return None, "doc-surface create line missing (45s)"
    return rect, None


def _cdp_engine_page(marker, deadline=30, cdp_port=9333):
    """CDP 找 native-host 页并等待引擎装载；返回 (pw, browser, page)。"""
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{cdp_port}")
    t0 = time.monotonic()
    page = None
    while time.monotonic() - t0 < 20 and page is None:
        for ctx in browser.contexts:
            for pg in ctx.pages:
                if "native-host.html" in pg.url and (not marker or marker in pg.url):
                    page = pg
                    break
        if page is None:
            time.sleep(1)
    if page is None:
        browser.close()
        pw.stop()
        return None, None, None
    eng = None
    while time.monotonic() - t0 < deadline:
        try:
            eng = page.evaluate("() => window.__probe ? window.__probe.engine : null")
        except Exception:
            eng = None
        if eng:
            break
        time.sleep(1)
    return pw, browser, (page if eng else None)


def _drag_para_and_verify(page, rect, win_hwnd, oracle_scan, sid, results,
                          tag="N-02"):
    """翻页至目标句 → 真实 SendInput 拖选 → sidecar/oracle 核验。

    定位纪律（t04-vm1 实测修正）：句子行盒经 JS Range 量测（量测用途，
    非代选——选择仍为真实 SendInput）；分页后 frame 可能整体切换，必须
    每轮重找 frame、以当前可见 rects 判定入视口，防止量测滞后于翻页。
    """
    wpx, hpx, ox, oy = rect
    vw = page.evaluate("() => window.innerWidth")
    vh = page.evaluate("() => window.innerHeight")
    line_box = None  # 页面级 css 坐标 {x,y,width,height}（目标句某一行盒）
    for _ in range(12):
        # 每轮重找承载目标句的 frame（翻页会换章节 iframe）。
        found_frame = None
        for f in page.frames:
            try:
                if REPEAT_A_MARKER in f.content():
                    found_frame = f
                    break
            except Exception:
                continue
        if found_frame is not None:
            try:
                # 入视口判定用页面视口（vw/vh 形参）而非 iframe 内窗——分栏
                # 排版下 iframe innerWidth 可达 2 倍视口宽（forensics3 实测
                # 1588 vs 848），iframe 口径会把屏外列误判可见。
                line_box = found_frame.evaluate(
                    """([marker, full, vw, vh]) => {
                        const walker = document.createTreeWalker(
                            document.body, NodeFilter.SHOW_TEXT);
                        const hits = [];
                        let n;
                        while ((n = walker.nextNode())) {
                            let i = 0;
                            while ((i = n.data.indexOf(marker, i)) >= 0) {
                                hits.push([n, i]);
                                i += marker.length;
                            }
                        }
                        if (hits.length < 2) return null;
                        const [node, off] = hits[1];  // 第 2 处出现（=ch1 para7）
                        const end = node.data.indexOf('。', off);
                        const r = document.createRange();
                        r.setStart(node, off);
                        r.setEnd(node, end > 0 ? end + 1 : off + full.length);
                        const rects = r.getClientRects();
                        const fe = frameElement
                            ? frameElement.getBoundingClientRect()
                            : {left: 0, top: 0};
                        for (const b of rects) {
                            const x = b.left + fe.left, y = b.top + fe.top;
                            if (b.width > 40 && b.height > 6 && x >= -4 && y >= -4
                                && x + b.width <= vw + 4
                                && y + b.height <= vh + 4) {
                                return {x, y, width: b.width, height: b.height,
                                        hits: hits.length};
                            }
                        }
                        return null;
                    }""", [REPEAT_A_MARKER, REPEAT_A, vw, vh])
            except Exception:
                line_box = None
        if line_box:
            break
        page.evaluate("() => window.__probe.view.renderer.next()")
        page.wait_for_timeout(900)
    if not line_box:
        results(tag, "FAIL", "target sentence line never visible (12 pages)")
        return None
    results(tag + ".target-visible", "PASS",
            f"2nd-occurrence line on page ({int(line_box['width'])}x{int(line_box['height'])} css, "
            f"occurrences={line_box.get('hits')})")

    # css → 宿主屏幕物理坐标：视口 = 子表面，比例 = wpx/innerWidth。
    vw = page.evaluate("() => window.innerWidth")
    scale = wpx / max(1, vw)
    cpt = ctypes.wintypes.POINT(0, 0)
    user32.ClientToScreen(win_hwnd, ctypes.byref(cpt))
    bx0 = cpt.x + ox + line_box["x"] * scale
    by0 = cpt.y + oy + line_box["y"] * scale
    bw = line_box["width"] * scale
    bh = line_box["height"] * scale
    # 逐点 hit-test 守卫（T-00 教训：覆盖层/误窗必须具名失败）。
    _, cls0 = _hit_window(bx0 + bw * 0.3, by0 + bh * 0.4)
    guard = ("Chrome" in cls0) or ("WRY" in cls0.upper())
    results(tag + ".hit-guard", "PASS" if guard else "FAIL", "hit=" + cls0)
    if not guard:
        return None
    fg_ok = False
    for _ in range(4):
        _force_foreground(win_hwnd)
        time.sleep(0.5)
        if user32.GetForegroundWindow() == win_hwnd:
            fg_ok = True
            break
    results(tag + ".foreground", "PASS" if fg_ok else "FAIL",
            "fg==hwnd:" + str(fg_ok))
    if not fg_ok:
        # 前台失守时拖选必然落点漂移（vm14 实测拖中 ch2 假锚点段）——具名
        # 失败，不带病拖选。
        results(tag, "FAIL", "window foreground could not be secured for drag")
        return None
    # 有界重试（2 次）：拖选后 CDP 读 DOM 选区——非空且含目标句片段才算
    # 拖选生效；空/漂移则重量测再拖（外部输入注入的环境方差；oracle 仍
    # 独立核验，不放宽）。
    JS_LINE = """([marker, vw, vh]) => {
        const walker = document.createTreeWalker(
            document.body, NodeFilter.SHOW_TEXT);
        const hits = [];
        let n;
        while ((n = walker.nextNode())) {
            let i = 0;
            while ((i = n.data.indexOf(marker, i)) >= 0) {
                hits.push([n, i]);
                i += marker.length;
            }
        }
        if (hits.length < 2) return null;
        const [node, off] = hits[1];
        const end = node.data.indexOf('\\u3002', off);
        const r = document.createRange();
        r.setStart(node, off);
        r.setEnd(node, end > 0 ? end + 1 : off + marker.length);
        const rects = r.getClientRects();
        const fe = frameElement
            ? frameElement.getBoundingClientRect()
            : {left: 0, top: 0};
        for (const b of rects) {
            const x = b.left + fe.left, y = b.top + fe.top;
            if (b.width > 40 && b.height > 6 && x >= -4 && y >= -4
                && x + b.width <= vw + 4
                && y + b.height <= vh + 4) {
                return {x, y, width: b.width, height: b.height};
            }
        }
        return null;
    }"""
    JS_SEL = """() => { const s = document.getSelection();
        return s && !s.isCollapsed ? s.toString() : null; }"""
    for attempt in (1, 2):
        fresh = None
        try:
            fresh = found_frame.evaluate(JS_LINE, [REPEAT_A_MARKER, vw, vh])
        except Exception:
            fresh = None
        if fresh:
            bx0 = cpt.x + ox + fresh["x"] * scale
            by0 = cpt.y + oy + fresh["y"] * scale
            bw = fresh["width"] * scale
            bh = fresh["height"] * scale
        sxp, syp = bx0 + bw * 0.30, by0 + bh * 0.40
        exp_, eyp = bx0 + bw * 0.92, by0 + bh * 0.75
        _send_mouse(sxp, syp)
        time.sleep(0.25)
        _send_mouse(sxp, syp, down=True)
        time.sleep(0.2)
        for i in range(1, 13):
            _send_mouse(sxp + (exp_ - sxp) * i / 12, syp + (eyp - syp) * i / 12)
            time.sleep(0.12)
        time.sleep(0.2)
        _send_mouse(exp_, eyp, down=False)
        time.sleep(2.5)
        sel_txt = None
        try:
            for f in page.frames:
                r = f.evaluate(JS_SEL)
                if r:
                    sel_txt = r
                    break
        except Exception:
            sel_txt = None
        # 选区接受口径：去空白后为 REPEAT_A 的子串（拖选可落在句中任意
        # 行段——行盒拖选常只覆盖句尾片段，t05-vm1 实测）；oracle 仍独立
        # 核验落盘记录的逐字/位次。
        flat = (sel_txt or "").replace(chr(10), "").replace(" ", "")
        if flat and flat in REPEAT_A:
            results(tag + ".drag-attempt" + str(attempt), "PASS",
                    "selection=" + repr(sel_txt[:36]))
            return True
        results(tag + ".drag-attempt" + str(attempt),
                "FAIL" if attempt == 2 else "RETRY",
                "selection=" + repr(str(sel_txt)[:36]))
    return None


# ─────────────────────── N-02 / N-03 / N-05(基础) 主流程 ───────────────────────

def run_vm(out_dir, corpus_dir, oracle_scan, results):
    """真实 AutoUI 原生 VM 消费者：N-02 全链 + N-03 冷恢复 + N-05 基础几何。"""
    data_dir = os.path.join(out_dir, "probe-data")
    reader_data = os.path.join(out_dir, "reader-data")
    import shutil
    for d in (data_dir, reader_data):
        shutil.rmtree(d, ignore_errors=True)
    assets_dir = os.environ.get("PROBE_ASSETS_DIR", "")
    tool_bin = os.environ.get("AUTO_UI_TOOL_BIN", "")
    if not os.path.isfile(os.path.join(assets_dir, "foliate-view.js")):
        results("N-02", "GAP", "engine assets missing: " + assets_dir)
        return
    if not tool_bin or not os.path.isfile(tool_bin):
        results("N-02", "GAP",
                "AUTO_UI_TOOL_BIN unset/missing (explicit cohort required)")
        return

    epub = os.path.join(corpus_dir, "probe-alpha.epub")
    reader_inst = Instance(HERE and os.path.abspath(os.path.join(HERE, "..", "..", "..")),
                           os.path.join(out_dir, "reader.log"),
                           {"AUTO_READER_DATA": reader_data})
    cons = None
    try:
        if not reader_inst.wait("http://127.0.0.1:17825/api/library/books"):
            results("N-02", "FAIL", "reader boot timeout")
            return
        r = _http("POST", "http://127.0.0.1:17825/api/library/import",
                  {"path": epub.replace("\\", "/"), "author": "PLAN-029",
                   "force": False}, timeout=120)
        if '"book_id"' not in json.dumps(r, ensure_ascii=False):
            results("N-02", "FAIL", "reader import failed")
            return
        books = _http("GET", "http://127.0.0.1:17825/api/library/books")
        bl = books.get("books") if isinstance(books, dict) else books
        target = next(b for b in bl if b.get("format") == "epub")
        bj = _http("GET", "http://127.0.0.1:17825/api/library/books/" + target["book_id"])
        ident = {"book_id": bj["book_id"], "source_hash": bj["source_hash"],
                 "managed_path": str(bj["managed_path"]).replace("\\", "/"),
                 "size": os.path.getsize(bj["managed_path"])}
        results("N-02.reader-import", "PASS",
                f"book_id={ident['book_id'][:13]}… managed={os.path.basename(ident['managed_path'])}")

        # WEBVIEW2_USER_DATA_FOLDER 按运行+实例隔离：默认 UDF 被历史孤儿
        # msedgewebview2（0x800700AA 资源占用实测）占用；同 UDF 跨实例重启
        # 也会竞态（t04-vm13 consumer2 实测）——每实例独立 UDF。
        def _make_env(seq):
            udf = os.path.join(out_dir, f"webview-udf-{seq}")
            shutil.rmtree(udf, ignore_errors=True)
            # CDP 端口也按实例隔离（9333/9334/9335）——旧实例 WebView2 退出
            # 异步释放端口，新实例同口重绑会 ECONNRESET（t04-vm19 实测）。
            cdp = 9332 + seq
            return {"PROBE_DATA_DIR": data_dir, "PROBE_ASSETS_DIR": assets_dir,
                    "PROBE_PUBLIC_BASE": "http://127.0.0.1:17827",
                    "AUTO_DOC_SURFACE_DEBUG": "1",
                    "WEBVIEW2_USER_DATA_FOLDER": udf,
                    "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS":
                        f"--remote-debugging-port={cdp}",
                    "AUTO_VM_WINDOW": "900x700",
                    "AUTO_VM_POSITION": "40,40"}
        env = _make_env(1)
        cons = VmInstance(APP_DIR, os.path.join(out_dir, "consumer.log"), env)
        if not cons.wait_http("http://127.0.0.1:17827/api/probe/health"):
            results("N-02", "FAIL", "consumer backend boot timeout")
            return
        mcp1 = _wait_mcp(os.path.join(out_dir, "consumer.log"))
        if not mcp1:
            results("N-02", "FAIL", "native session MCP endpoint not announced (90s)")
            return
        _http("POST", "http://127.0.0.1:17827/api/probe/register",
              {"book_id": ident["book_id"], "source_hash": ident["source_hash"],
               "managed_path": ident["managed_path"], "title": "probe-alpha",
               "book_bytes": ident["size"]})
        sid = "vm-" + str(int(time.time()))
        _http("POST", "http://127.0.0.1:17827/api/probe/session",
              {"session_id": sid, "book_id": ident["book_id"],
               "source_hash": ident["source_hash"], "engine": ENGINE_REVISION})

        snap = _wait_tree(mcp1)
        results("N-02.native-tree", "PASS" if "doc-surface" in snap else "FAIL",
                "doc-surface in MCP tree=" + str("doc-surface" in snap))
        rect, err = _connect_session(mcp1, sid, os.path.join(out_dir, "consumer.log"))
        if not rect:
            results("N-02", "FAIL", err)
            return
        results("N-02.surface-created", "PASS",
                f"phys={rect[0]}x{rect[1]}@{rect[2]},{rect[3]}")

        pw, browser, page = _cdp_engine_page(sid)
        if page is None:
            results("N-02.engine-mount", "FAIL", "engine page/mount not via CDP (30s)")
            try:
                browser.close()
                pw.stop()
            except Exception:
                pass
            return
        eng = page.evaluate("() => window.__probe.engine")
        results("N-02.engine-mount", "PASS", f"engine={eng} (budget 15s)")

        win_pid = _probe_window_pid()
        hits = _find_windows_of_pid(win_pid) if win_pid else []
        win_hwnd = max(hits, key=lambda h: _client_size(h)[0] * _client_size(h)[1]) \
            if hits else None
        if not win_hwnd:
            results("N-02", "FAIL", "native window not found for input")
            browser.close()
            pw.stop()
            return
        ok = _drag_para_and_verify(page, rect, win_hwnd, oracle_scan, sid, results)
        browser.close()
        pw.stop()
        if not ok:
            return

        side = _http("GET", f"http://127.0.0.1:17827/api/probe/locators?session_id={sid}")
        recs = side.get("sidecar", {}).get("records", []) if side.get("found") else []
        results("N-02.real-drag", "PASS" if recs else "FAIL",
                f"records={len(recs)} after real SendInput drag")
        if not recs:
            return
        # adapter 对 selectionchange 连发多 POST（含拖选中间态）——核验对象
        # = 目标句的记录（拖选可从句中任意处起，标记前缀不必然在引文内；
        # 「琥珀色的狐狸跃过懒狗」为 REPEAT_A 特有片段）。oracle 仍独立
        # 逐字/位次核验，不放宽。
        def _is_target_quote(q):
            flat = (q or "").replace(chr(10), "").replace(" ", "")
            return bool(flat) and (flat in REPEAT_A or REPEAT_A in flat)
        tgt = [r for r in recs
               if _is_target_quote(r["locator"]["text_quote"])]
        if not tgt:
            results("N-02", "FAIL",
                    "no record carries the target sentence; quotes="
                    + "; ".join(r["locator"]["text_quote"][:14] for r in recs[:4]))
            return
        rec = tgt[-1]
        quote = rec["locator"]["text_quote"]
        occ = int(rec["locator"]["occurrence"])
        vq = oracle_scan.verify_quote(quote, occ)
        results("N-02.quote-oracle", "PASS" if vq.get("ok") else "FAIL",
                f"occ={occ} ok={vq.get('ok')} pos={vq.get('position')} "
                f"occurrences={vq.get('occurrences')}")
        results("N-02.cfi-present",
                "PASS" if str(rec["locator"]["cfi"]).startswith("epubcfi") else "FAIL",
                "cfi=" + str(rec["locator"]["cfi"])[:56])
        disk = os.path.join(data_dir, "probe", "locators", sid + ".json")
        ok_disk = False
        if os.path.exists(disk):
            try:
                dj = json.load(open(disk, encoding="utf-8"))
                ok_disk = any(rr.get("locator", {}).get("text_quote") == quote
                              for rr in dj.get("records", []))
            except Exception:
                ok_disk = False
        results("N-02.sidecar-disk", "PASS" if ok_disk else "FAIL", disk)
        # 计数前静默：adapter 会因 selectionchange 连发多 POST（t04-vm1
        # 实测 1→3），读数必须等计数稳定再冻结基线。
        def _count():
            sj = _http("GET", f"http://127.0.0.1:17827/api/probe/locators?session_id={sid}")
            rr = sj.get("sidecar", {}).get("records", []) if sj.get("found") else []
            return len(rr)
        n_saved = _count()
        for _ in range(5):
            time.sleep(1.5)
            n2 = _count()
            if n2 == n_saved:
                break
            n_saved = n2
        results("N-02.settle", "PASS", f"record count settled at {n_saved}")

        # ── N-03：正常关闭 → 新进程冷恢复 ──
        cons.stop()
        time.sleep(2)
        env = _make_env(2)
        cons = VmInstance(APP_DIR, os.path.join(out_dir, "consumer2.log"), env)
        if not cons.wait_http("http://127.0.0.1:17827/api/probe/health"):
            results("N-03", "FAIL", "consumer restart (normal close) timeout")
            return
        mcp2 = _wait_mcp(os.path.join(out_dir, "consumer2.log"))
        sid2 = sid + "r"
        _http("POST", "http://127.0.0.1:17827/api/probe/session",
              {"session_id": sid2, "book_id": ident["book_id"],
               "source_hash": ident["source_hash"], "engine": ENGINE_REVISION})
        rect2, err = _connect_session(mcp2, sid2, os.path.join(out_dir, "consumer2.log"))
        if not rect2:
            results("N-03", "FAIL", "restart connect: " + err)
            return
        ok_restore, err = False, ""
        pw, browser, page2 = _cdp_engine_page(sid2, cdp_port=9334)
        if page2 is None:
            err = "restored engine page not found (CDP)"
        else:
            t0 = time.monotonic()
            while time.monotonic() - t0 < 30:
                try:
                    r = page2.evaluate(
                        "async (cfi) => { try { await window.__probe.view.goTo(cfi);"
                        " return 'ok'; } catch (e) { return 'err:' + e; } }",
                        rec["locator"]["cfi"])
                    if r == "ok":
                        txt = page2.evaluate(
                            "(t) => { const cs = window.__probe.view.renderer.getContents();"
                            " for (const c of cs) { if (c.doc.body &&"
                            " c.doc.body.textContent.includes(t)) return true; }"
                            " return false; }",
                            quote[:18])
                        if txt:
                            ok_restore = True
                            break
                    err = r
                except Exception as e:
                    err = repr(e)[:80]
                time.sleep(1.5)
        if pw:
            try:
                browser.close()
                pw.stop()
            except Exception:
                pass
        results("N-03.cold-restore-normal",
                "PASS" if ok_restore else "FAIL",
                f"goto={err or 'ok'} target-visible={ok_restore} (deadline 30s)")
        side2 = _http("GET", f"http://127.0.0.1:17827/api/probe/locators?session_id={sid}")
        recs2 = side2.get("sidecar", {}).get("records", []) if side2.get("found") else []
        results("N-03.old-records-preserved",
                "PASS" if len(recs2) == n_saved else "FAIL",
                f"before={n_saved} after={len(recs2)}")

        # 异常退出（强杀树）→ 数据仍在 + 可再启动。
        cons.kill_hard()
        time.sleep(2)
        env = _make_env(3)
        cons = VmInstance(APP_DIR, os.path.join(out_dir, "consumer3.log"), env)
        if not cons.wait_http("http://127.0.0.1:17827/api/probe/health"):
            results("N-03.crash-restart", "FAIL", "restart after hard kill timeout")
            return
        results("N-03.crash-restart", "PASS", "backend up after hard kill")
        side3 = _http("GET", f"http://127.0.0.1:17827/api/probe/locators?session_id={sid}")
        recs3 = side3.get("sidecar", {}).get("records", []) if side3.get("found") else []
        results("N-03.data-survives-crash",
                "PASS" if len(recs3) == n_saved else "FAIL",
                f"records={len(recs3)}")

        # N-05 基础几何：resize 后表面 rect 跟随（create/move 行取证）；
        # 完整 resize/遮挡/隐藏重拖选门随 T-05 正式化。
        mcp3 = _wait_mcp(os.path.join(out_dir, "consumer3.log"))
        sid3 = sid + "g"
        _http("POST", "http://127.0.0.1:17827/api/probe/session",
              {"session_id": sid3, "book_id": ident["book_id"],
               "source_hash": ident["source_hash"], "engine": ENGINE_REVISION})
        rect3, err = _connect_session(mcp3, sid3, os.path.join(out_dir, "consumer3.log"))
        if not rect3:
            results("N-05.resize-follow", "FAIL", "reconnect: " + err)
            return
        # 重启后窗口进程全新——hwnd 必须重解析（旧 hwnd 已失效，MoveWindow
        # 无效即本门第一次实跑的 FAIL 根因）。
        win_pid3 = _probe_window_pid()
        hits3 = _find_windows_of_pid(win_pid3) if win_pid3 else []
        win_hwnd3 = max(hits3, key=lambda h: _client_size(h)[0] * _client_size(h)[1]) \
            if hits3 else None
        if not win_hwnd3:
            results("N-05.resize-follow", "FAIL", "restarted native window not found")
            return
        # ── N-04 先于 resize：WebView2 set_bounds 后（N-05 resize）父窗点击
        # 聚焦会间歇失效（t04-vm6/8/9/11 互现）；pin 几何 + 表面在场已证
        # 可靠（n04-forensics8 B/C）。resize 后的门（N-05）保持最后。
        _run_ime_n04(mcp3, win_hwnd3, results, rect=rect3, cdp_port=9335)
        # 物理 (1400x1300) = 逻辑 700x650——必须大于表面高（420 逻辑）+页头，
        # 否则 canvas 裁剪出客户区 → sync 静默隐藏（t03-vm4 实测教训）。
        user32.MoveWindow(win_hwnd3, 100, 100, 1400, 1300, True)
        time.sleep(2.5)
        # resize 后从最近日志行取最新 rect（move 行）核对跟随。
        last = None
        with open(os.path.join(out_dir, "consumer3.log"), encoding="utf-8",
                  errors="replace") as f:
            for line in f:
                if "[doc-surface #" in line and ("] move " in line or "] sync " in line):
                    m = re.search(r"phys=(\d+)x(\d+)@(\d+),(\d+)", line)
                    if m:
                        last = tuple(int(g) for g in m.groups())
        followed = last is not None and last != rect3 and last[2] < 400
        results("N-05.resize-follow", "PASS" if followed else "FAIL",
                f"before={rect3} after={last}")
    finally:
        if cons:
            cons.stop()
        reader_inst.stop()


# ─────────────────────── N-04：IME/焦点门（T-04） ───────────────────────

def _send_key(vk, extended=0):
    """单键 down/up（真实 OS 键盘事件）。"""
    user32.keybd_event(vk, 0, extended, 0)
    user32.keybd_event(vk, 0, extended | 2, 0)


def _send_char(ch):
    vk = user32.VkKeyScanW(ord(ch))
    shift = (vk >> 8) & 1
    code = vk & 0xFF
    for d in (0, 2):
        if shift:
            user32.keybd_event(0x10, 0, d, 0)
        user32.keybd_event(code, 0, d, 0)
        if shift:
            user32.keybd_event(0x10, 0, d, 0)


def _click_twice(px, py):
    """两段式真实点击：首击激活窗口，次击投递控件（未激活窗首击被吞——
    n04 forensics 实测扫描失败的成因之一）。"""
    for _ in range(2):
        _send_mouse(px, py, True)
        time.sleep(0.06)
        _send_mouse(px, py, False)
        time.sleep(0.35)


def _ime_input_value(mcp_base):
    t = _mcp_text(mcp_base, "autoui_snapshot")
    m = re.search(r'input[^\n]*\{[^}]*value: "([^"]*)"', t)
    return m.group(1) if m else None


def _run_ime_n04(mcp_base, win_hwnd, results, tag="N-04", rect=None,
                 cdp_port=9333):
    """真实 IME 门：真实点击聚焦输入框（行内扫描+键击核验）→ MS Pinyin
    组合/提交 → Esc 取消 → 组合期快捷键不触发页面命令 → 焦点往返
    （输入框↔文档表面，值变化/CDP 选区为归属证据）。"""
    import urllib.request

    def mcp_text(name, args=None):
        return _mcp_text(mcp_base, name, args)

    cpt = ctypes.wintypes.POINT(0, 0)
    user32.ClientToScreen(win_hwnd, ctypes.byref(cpt))
    ox, oy = cpt.x, cpt.y
    dpi = user32.GetDpiForWindow(win_hwnd) or 96
    scale = dpi / 96.0
    cw, chh = _client_size(win_hwnd)
    lw, lh = cw / scale, chh / scale

    _force_foreground(win_hwnd)
    time.sleep(0.4)
    if user32.GetForegroundWindow() != win_hwnd:
        results(tag, "GAP", "window foreground could not be secured")
        return

    # 真实点击聚焦输入框：几何推算（页面列 max-w-4xl 居中 + 头行固定偏移，
    # n04-forensics5 实测命中）+ 有限偏移重试。散点扫射会打出杂散 IME 组合
    # 态/候选窗吞掉后续点击——必须单点精准。
    col_left = max(24.0, (lw - 896.0) / 2.0 + 24.0)
    base_x = col_left + 273.0  # 输入框中心（256 宽，行内偏移 145+128）
    found_x = None
    tries = []
    v0 = _ime_input_value(mcp_base)
    # 捕获态冲刷：N-02 的真实拖选可能让 Chromium 持有鼠标捕获（button-up
    # 竞态），后续父窗点击全被路由进 webview——先在表面内补一次完整
    # down+up，并在每次尝试记录 hwndCapture。
    class GUIINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("flags", ctypes.c_uint),
                    ("hwndActive", ctypes.c_void_p), ("hwndFocus", ctypes.c_void_p),
                    ("hwndCapture", ctypes.c_void_p), ("hwndMenuOwner", ctypes.c_void_p),
                    ("hwndMoveSize", ctypes.c_void_p), ("hwndCaret", ctypes.c_void_p),
                    ("rcCaret", ctypes.wintypes.RECT)]
    def capture_hwnd():
        gi = GUIINFO()
        gi.cbSize = ctypes.sizeof(gi)
        user32.GetGUIThreadInfo(0, ctypes.byref(gi))
        return gi.hwndCapture or 0
    if rect is not None:
        fw, fh, fox, foy = rect
        cpt0 = ctypes.wintypes.POINT(0, 0)
        user32.ClientToScreen(win_hwnd, ctypes.byref(cpt0))
        fx0 = cpt0.x + fox + fw // 2
        fy0 = cpt0.y + foy + fh // 2
        _send_mouse(fx0, fy0, True)
        time.sleep(0.08)
        _send_mouse(fx0, fy0, False)
        time.sleep(0.6)
        tries.append(f"flush capture={capture_hwnd():#x}")
    # y 带容差（布局基线 ±10 逻辑px），先 ESC 清残留组合再试（杂散组合态
    # 会吞后续键击——t04-vm6/8 通过与失败互现的根因面）。
    for gy in (105, 95, 115):
        for dx in (0, -24, 24, -48, 48):
            fx = base_x + dx
            if fx < col_left + 8 or fx > lw - 8:
                continue
            px, py = ox + int(fx * scale), oy + int(gy * scale)
            _, hit_cls = _hit_window(px, py)
            cap = capture_hwnd()
            _send_key(0x1B)  # ESC：清掉任何残留 IME 组合
            time.sleep(0.3)
            _force_foreground(win_hwnd)
            time.sleep(0.3)
            _click_twice(px, py)
            time.sleep(0.6)
            _send_char("q")
            time.sleep(0.2)
            _send_key(0x0D)  # 组合中 Enter=提交原文（MS Pinyin），值才可见
            time.sleep(1.0)
            v1 = _ime_input_value(mcp_base)
            tries.append(f"x{fx:.0f}y{gy}:{hit_cls}:cap{cap:#x}:{v1!r}")
            if v1 is not None and (v0 is None or v1 != v0):
                found_x = fx
                found_y = gy
                break
            v0 = v1
        if found_x is not None:
            break
    if found_x is None:
        results(tag + ".input-focus", "FAIL",
                f"real-click focus failed; tries={tries}")
        return
    results(tag + ".input-focus", "PASS",
            f"real click+keystroke focus at logical ({found_x:.0f},{found_y})")

    def click_input():
        px, py = ox + int(found_x * scale), oy + int(105 * scale)
        _force_foreground(win_hwnd)
        time.sleep(0.3)
        _click_twice(px, py)
        time.sleep(0.4)

    # ① 组合 + Esc 取消 → 值不变。
    click_input()
    before = _ime_input_value(mcp_base)
    for ch in "ni":
        _send_char(ch)
        time.sleep(0.15)
    time.sleep(0.4)
    _send_key(0x1B)  # Esc 取消组合
    time.sleep(1.0)
    after = _ime_input_value(mcp_base)
    cancel_ok = after == before
    results(tag + ".ime-cancel", "PASS" if cancel_ok else "FAIL",
            f"before={before!r} after={after!r} (Esc cancels composition)")

    # ② 组合 + Space 提交 → 值以中文落定（唯一能拉丁→汉字的管线=IME）。
    click_input()
    base = _ime_input_value(mcp_base)
    for ch in "nihao":
        _send_char(ch)
        time.sleep(0.15)
    time.sleep(0.4)
    _send_key(0x20)  # Space 首选转换提交
    time.sleep(1.3)
    committed = _ime_input_value(mcp_base)
    has_cjk = committed is not None and committed != base and \
        any('\u4e00' <= c <= '\u9fff' for c in committed)
    results(tag + ".ime-commit", "PASS" if has_cjk else "FAIL",
            f"before={base!r} after={committed!r}")

    # ③ 组合期快捷键：组合中按 Enter——MS Pinyin 语义=提交原文拉丁，
    # 不触发页面命令；核验：仅期望增量，session_state/表面不变。
    click_input()
    pre = _ime_input_value(mcp_base)
    state_pre = "connected" in _mcp_text(mcp_base, "autoui_snapshot")
    for ch in "zh":
        _send_char(ch)
        time.sleep(0.15)
    time.sleep(0.3)
    _send_key(0x0D)  # Enter（组合中）——须只提交原文，不得触发页面命令
    time.sleep(1.2)
    post = _ime_input_value(mcp_base)
    state_post = "connected" in _mcp_text(mcp_base, "autoui_snapshot")
    # 插入点=点击处（可在文本中部）：核验语义而非位置——pre 是 post 的
    # 子序列、长度恰 +2（原文 zh 提交）、页面状态不变（无命令误触）。
    def _subseq(small, big):
        it = iter(big)
        return all(c in it for c in small)
    hotkey_ok = (post is not None and pre is not None
                 and len(post) == len(pre) + 2
                 and _subseq(pre or "", post)
                 and state_post == state_pre)
    results(tag + ".hotkey-in-composition",
            "PASS" if hotkey_ok else "FAIL",
            f"value {pre!r}->{post!r} state_kept={state_post == state_pre} "
            f"(Enter commits raw at caret, no page command)")

    # ④ 焦点往返：输入框 → 文档表面（点击+真实拖选产选择）→ 输入框（键击变值）。
    click_input()
    _send_char("m")
    time.sleep(0.2)
    _send_key(0x0D)
    time.sleep(0.8)
    v_in = _ime_input_value(mcp_base)
    # 点击表面中心（logical 居中偏下，避开页头；物理换算）。
    sx0 = ox + int(lw * 0.5 * scale)
    sy0 = oy + int((lh * 0.45) * scale)
    _click_twice(sx0, sy0)
    time.sleep(0.6)
    # 表面内小拖选（真实输入）→ CDP 选区归属证据。
    from playwright.sync_api import sync_playwright
    sel_ok = False
    try:
        pw = sync_playwright().start()
        browser = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{cdp_port}")
        page = None
        for ctx in browser.contexts:
            for pg in ctx.pages:
                if "native-host.html" in pg.url:
                    page = pg
                    break
        if page is not None:
            _send_mouse(sx0 - 80, sy0, True)
            time.sleep(0.1)
            for i in range(1, 9):
                _send_mouse(sx0 - 80 + 20 * i, sy0 + 12)
                time.sleep(0.08)
            time.sleep(0.15)
            _send_mouse(sx0 + 80, sy0 + 12, False)
            time.sleep(1.5)
            for f in page.frames:
                try:
                    s = f.evaluate(
                        "() => { const s = document.getSelection();"
                        " return s && !s.isCollapsed ? s.toString().slice(0, 30) : null; }")
                    if s:
                        sel_ok = True
                        break
                except Exception:
                    continue
        browser.close()
        pw.stop()
    except Exception as e:
        results(tag + ".focus-roundtrip", "GAP", "CDP unavailable: " + repr(e)[:80])
        return
    v_after_surface = _ime_input_value(mcp_base)
    class GUIINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("flags", ctypes.c_uint),
                    ("hwndActive", ctypes.c_void_p), ("hwndFocus", ctypes.c_void_p),
                    ("hwndCapture", ctypes.c_void_p), ("hwndMenuOwner", ctypes.c_void_p),
                    ("hwndMoveSize", ctypes.c_void_p), ("hwndCaret", ctypes.c_void_p),
                    ("rcCaret", ctypes.wintypes.RECT)]
    # 回到输入框：真实键击必须再改值（焦点已返回）。表面拖选后 Chromium
    # 可能仍持鼠标捕获（后续父窗点击被路由进 webview）——先在表面内补
    # 一次完整 down+up 冲刷捕获，再重点击输入框；有界重试。
    v_back = v_after_surface
    WM_CANCELMODE = 0x001F
    rt_log = []
    for attempt_i in range(4):
        # 捕获/焦点取证：表面拖选后 Chromium 可能仍持捕获或 OS 焦点停在
        # 弹出窗内——点击与键击被路由进 webview。捕获持有时 WM_CANCELMODE。
        gi = GUIINFO()
        gi.cbSize = ctypes.sizeof(gi)
        user32.GetGUIThreadInfo(0, ctypes.byref(gi))
        cap = gi.hwndCapture or 0
        fpre = gi.hwndFocus or 0
        if cap and cap != win_hwnd:
            user32.PostMessageW(cap, WM_CANCELMODE, 0, 0)
            time.sleep(0.4)
        # 显式焦点归还（点击激活的内部机制）：AttachThreadInput 后 SetFocus
        # 到 iced 主窗——表面拖选后 OS 线程焦点停在弹出窗 Chrome（fd5e 类，
        # 拟人点击也无法拉回的合成输入盲区）。
        fgw = user32.GetForegroundWindow()
        tid_fg = user32.GetWindowThreadProcessId(fgw, None)
        tid_me = kernel32.GetCurrentThreadId()
        user32.AttachThreadInput(tid_me, tid_fg, True)
        user32.SetFocus(win_hwnd)
        user32.AttachThreadInput(tid_me, tid_fg, False)
        time.sleep(0.3)
        _send_mouse(sx0, sy0, True)
        time.sleep(0.06)
        _send_mouse(sx0, sy0, False)
        time.sleep(0.5)
        if attempt_i % 2 == 1:
            # 拟人路径：先点标题栏（激活 iced 窗、OS 焦点归位），再点输入框。
            wr = ctypes.wintypes.RECT()
            user32.GetWindowRect(win_hwnd, ctypes.byref(wr))
            _send_mouse(wr.left + 300, wr.top + 20, True)
            time.sleep(0.06)
            _send_mouse(wr.left + 300, wr.top + 20, False)
            time.sleep(0.5)
        click_input()
        _send_char("k")
        time.sleep(0.2)
        _send_key(0x0D)
        time.sleep(0.9)
        v_try = _ime_input_value(mcp_base)
        gi2 = GUIINFO()
        gi2.cbSize = ctypes.sizeof(gi2)
        user32.GetGUIThreadInfo(0, ctypes.byref(gi2))
        rt_log.append(
            f"a{attempt_i}:cap{cap & 0xFFFF:x} f{fpre & 0xFFFF:x}"
            f"->f{(gi2.hwndFocus or 0) & 0xFFFF:x} v={v_try!r}")
        if v_try is not None and v_try != v_after_surface:
            v_back = v_try
            break
    trip = sel_ok and v_back != v_after_surface
    results(tag + ".focus-roundtrip",
            "PASS" if trip else "FAIL",
            f"sel={sel_ok} v {v_after_surface!r}->{v_back!r} log={';'.join(rt_log)[:170]}")
    # 父用例 N-04 由聚合器按子项最坏推导（缺项/GAP/FAIL→非零）。
