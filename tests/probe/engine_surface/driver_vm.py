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


def _mcp_text_safe(base, name, args=None):
    """轮询专用：端点瞬时不可连（announce 先于 listener 就绪/端口释放竞态，
    green5 实测 10061）返回空串，不让轮询循环直接崩出。"""
    try:
        return _mcp_text(base, name, args)
    except Exception:
        return ""


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
    """等待原生树就绪（首帧构建；快照过早返回空树；瞬时拒连重试）。"""
    t0 = time.monotonic()
    while time.monotonic() - t0 < deadline:
        snap = _mcp_text_safe(mcp_base, "autoui_snapshot")
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
        if "connected" in _mcp_text_safe(mcp_base, "autoui_snapshot"):
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
                        # force-renderer-accessibility：Chromium 可达性树按需
                        # 激活对纯 UIA 客户端查询未生效（red2 实测 17 节点只见
                        # 窗口壳）——屏读/ Narrator 实效等价开关；UIA 读取的
                        # 仍是真实系统树，非 DOM ARIA。
                        f"--remote-debugging-port={cdp} "
                        f"--force-renderer-accessibility",
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
        if followed:
            # ── T-05 扩展门：字体重排/滚动重拖/遮挡/隐藏展示/UIA/键盘
            # （+交互 DPI 门，PROBE_DPI_INTERACTIVE=1）──
            _run_t05_gates(out_dir, mcp3, sid3, win_hwnd3, oracle_scan,
                           results, n_saved)
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
    t = _mcp_text_safe(mcp_base, "autoui_snapshot")
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


# ─────────────────────── N-05/N-06 扩展门（T-05） ───────────────────────
# 坐标纪律：屏幕几何一律驱动侧实测（EnumWindows 命中 doc_surface.rs 注册的
# 弹出窗类 AutoUIDocSurfacePopup + GetWindowRect 物理矩形），不以日志行为
# 坐标基准（T-02 子表面形态的 create 行按客户区相对口径解析，57cf408a 弹出
# 窗形态同一行已是屏幕绝对——两种口径并存，只有驱动侧实测与真实窗口一致）。
# 内容坐标：弹出窗物理宽 / webview css innerWidth = 内容→屏幕比例；行盒经
# JS Range 量测（量测用途，非代选——选择仍为真实 SendInput）。

POPUP_CLASS = "AutoUIDocSurfacePopup"


def _find_popup_hwnd():
    """doc-surface 弹出窗（按注册类名+可见性）。隐藏后必须查无——该函数
    即 N-05 隐藏门的真值来源。"""
    hits = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(h, _l):
        buf = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(h, buf, 64)
        if buf.value == POPUP_CLASS and user32.IsWindowVisible(h):
            hits.append(h)
        return True

    user32.EnumWindows(cb, None)
    return hits[0] if hits else None


def _win_rect(hwnd):
    """GetWindowRect 物理 (x, y, w, h)。弹出窗无边框客户区=窗口矩形。"""
    r = ctypes.wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return (r.left, r.top, r.right - r.left, r.bottom - r.top)


def _screen_pixel(x, y):
    """GDI 屏幕取样（DWM 合成后的真实像素，遮挡/显隐的真值探针）。
    GetPixel 属 gdi32（user32 无此导出——red2 实测 AttributeError）。"""
    hdc = user32.GetDC(0)
    c = ctypes.windll.gdi32.GetPixel(hdc, int(x), int(y))
    user32.ReleaseDC(0, hdc)
    if c < 0:  # CLR_INVALID
        return (-1, -1, -1)
    return (c & 0xFF, (c >> 8) & 0xFF, (c >> 16) & 0xFF)


_OCCLUDE_CLS = None


def _overlay_window(x, y, w, h):
    """驱动自有真实遮挡窗：WS_POPUP topmost 纯色底——语义等价其他应用浮窗
    覆盖（弹出窗非 topmost、z 跟随 owner，被浮窗盖住与普通窗口一致）。
    返回 (hwnd, brush)；用完必须 _drop_overlay。"""
    global _OCCLUDE_CLS
    WS_POPUP, WS_VISIBLE = 0x80000000, 0x10000000
    WS_EX_TOPMOST = 0x8
    # CreateSolidBrush/DeleteObject 属 gdi32（red2/3 同族误置 user32）。
    brush = ctypes.windll.gdi32.CreateSolidBrush(0x000000FF)  # COLORREF 0x00bbggrr = 红
    if not _OCCLUDE_CLS:
        class WNDCLASSW(ctypes.Structure):
            _fields_ = [("style", ctypes.c_uint), ("lpfnWndProc", ctypes.c_void_p),
                        ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                        ("hInstance", ctypes.c_void_p), ("hIcon", ctypes.c_void_p),
                        ("hCursor", ctypes.c_void_p), ("hbrBackground", ctypes.c_void_p),
                        ("lpszMenuName", ctypes.c_void_p), ("lpszClassName", ctypes.c_wchar_p)]
        wc = WNDCLASSW()
        wc.lpfnWndProc = ctypes.cast(user32.DefWindowProcW, ctypes.c_void_p).value
        wc.hInstance = kernel32.GetModuleHandleW(None)
        wc.hbrBackground = ctypes.c_void_p(brush)
        wc.lpszClassName = "AutoUIProbeOccluder"
        atom = user32.RegisterClassW(ctypes.byref(wc))
        if not atom:
            user32.DeleteObject(brush)
            raise OSError("RegisterClassW(occluder) failed")
        _OCCLUDE_CLS = wc.lpszClassName
    hwnd = user32.CreateWindowExW(WS_EX_TOPMOST, _OCCLUDE_CLS, "probe-occluder",
                                  WS_POPUP | WS_VISIBLE, int(x), int(y),
                                  int(w), int(h), 0, 0,
                                  kernel32.GetModuleHandleW(None), 0)
    if not hwnd:
        user32.DeleteObject(brush)
        raise OSError("CreateWindowExW(occluder) failed")
    return hwnd, brush


def _drop_overlay(hwnd, brush):
    if hwnd:
        user32.DestroyWindow(hwnd)
    if brush:
        ctypes.windll.gdi32.DeleteObject(brush)


# 行盒量测（页面级 css 坐标，frameElement 偏移并入）——与 N-02 同源口径。
_JS_LINE = """([marker, vw, vh]) => {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
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
    const fe = frameElement ? frameElement.getBoundingClientRect() : {left: 0, top: 0};
    for (const b of rects) {
        const x = b.left + fe.left, y = b.top + fe.top;
        if (b.width > 40 && b.height > 6 && x >= -4 && y >= -4
            && x + b.width <= vw + 4 && y + b.height <= vh + 4) {
            return {x, y, width: b.width, height: b.height};
        }
    }
    return null;
}"""
_JS_SEL = """() => { const s = document.getSelection();
    return s && !s.isCollapsed ? s.toString() : null; }"""
_JS_FIRST_LINE = """() => {
    // 逐字符量测（同行连续段）：整节点 rect 口径取到"句尾句号行"（green4
    // 选区塌缩成单字符）；首末可见字符跨度跨行时 40% 高度拖选也会塌缩
    // （green7 实测 3 字符短句）——取最长同行连续段，拖选必落同一行内。
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let n;
    const vw = window.innerWidth, vh = window.innerHeight;
    while ((n = walker.nextNode())) {
        const t = n.data;
        if (t.trim().length < 8) continue;
        const fe = frameElement ? frameElement.getBoundingClientRect() : {left: 0, top: 0};
        const vis = [];
        for (let i = 0; i < t.length; i++) {
            if (!t[i].trim()) continue;
            const r = document.createRange();
            r.setStart(n, i);
            r.setEnd(n, i + 1);
            const b = r.getBoundingClientRect();
            const x = b.left + fe.left, y = b.top + fe.top;
            if (b.width > 0 && b.height > 6 && x >= 0 && y >= 0
                && x + b.width <= vw && y + b.height <= vh) {
                vis.push({ x, y, w: b.width, h: b.height });
            }
        }
        // 最长同行连续段（y 差≤2px）——跨行 box 的 40% 高度拖选会塌缩
        // （green7 实测 3 字符短句），拖选必须落在同一行内。
        let best = null, run = [];
        for (const v of vis) {
            if (run.length && Math.abs(v.y - run[run.length - 1].y) > 2) {
                if (!best || run.length > best.length) best = run;
                run = [];
            }
            run.push(v);
        }
        if (!best || run.length > best.length) best = run;
        if (best && best.length >= 6) {
            const x1 = best[best.length - 1].x + best[best.length - 1].w;
            return { x: best[0].x, y: best[0].y, width: x1 - best[0].x,
                     height: best[0].h,
                     text: t.slice(best[0].i, best[best.length - 1].i + 1)
                               .slice(0, 24) + '…' };
        }
    }
    return null;
}"""


def _measure_target_line(page, deadline=15):
    """翻页至目标句可见并返回其页面级行盒（css）。每轮重找 frame——分页会
    换章节 iframe（N-02 同纪律）。"""
    vw = page.evaluate("() => window.innerWidth")
    vh = page.evaluate("() => window.innerHeight")
    for _ in range(12):
        for f in page.frames:
            try:
                if REPEAT_A_MARKER not in f.content():
                    continue
                lb = f.evaluate(_JS_LINE, [REPEAT_A_MARKER, vw, vh])
                if lb:
                    return lb
            except Exception:
                continue
        try:
            page.evaluate("() => window.__probe.view.renderer.next()")
        except Exception:
            pass
        page.wait_for_timeout(900)
    return None


def _popup_owner(x, y):
    """含屏幕点的弹出窗的 owner（iced 主窗）——前台核验用。"""
    h = _find_popup_hwnd()
    if not h:
        return None
    r = _win_rect(h)
    if not (r[0] <= x < r[0] + r[2] and r[1] <= y < r[1] + r[3]):
        return None
    return user32.GetWindow(h, 4)  # GW_OWNER


def _drag_line(page, popup_rect, line, owner_hwnd):
    """量测行盒 → 真实拖选（2 段式，逐点移动）；返回 CDP 读到的选区文本。"""
    px, py, pw, _ph = popup_rect
    vw = page.evaluate("() => window.innerWidth")
    scale = pw / max(1, vw)
    bx = px + line["x"] * scale
    by = py + line["y"] * scale
    bw = line["width"] * scale
    bh = line["height"] * scale
    _, cls0 = _hit_window(bx + bw * 0.3, by + bh * 0.4)
    if not (("Chrome" in cls0) or ("WRY" in cls0.upper())):
        return None, "hit=" + cls0
    for _ in range(3):
        _force_foreground(owner_hwnd)
        time.sleep(0.4)
        if user32.GetForegroundWindow() == owner_hwnd:
            break
    else:
        return None, "foreground lost"
    sxp, syp = bx + bw * 0.30, by + bh * 0.40
    exp_, eyp = bx + bw * 0.92, by + bh * 0.75
    _send_mouse(sxp, syp)
    time.sleep(0.25)
    _send_mouse(sxp, syp, down=True)
    time.sleep(0.2)
    for i in range(1, 13):
        _send_mouse(sxp + (exp_ - sxp) * i / 12, syp + (eyp - syp) * i / 12)
        time.sleep(0.1)
    time.sleep(0.2)
    _send_mouse(exp_, eyp, down=False)
    time.sleep(2.2)
    sel = None
    for f in page.frames:
        try:
            r = f.evaluate(_JS_SEL)
        except Exception:
            r = None
        if r:
            sel = r
            break
    return sel, None


def _poll_target_record(sid, base_count, deadline=12):
    """sidecar 记录数超过基线后，返回最新目标句记录（无则 None）。"""
    t0 = time.monotonic()
    recs = []
    while time.monotonic() - t0 < deadline:
        sj = _http("GET", f"http://127.0.0.1:17827/api/probe/locators?session_id={sid}")
        recs = sj.get("sidecar", {}).get("records", []) if sj.get("found") else []
        if len(recs) > base_count:
            time.sleep(1.5)  # selectionchange 连发中间态——等计数稳定
            sj = _http("GET", f"http://127.0.0.1:17827/api/probe/locators?session_id={sid}")
            recs = sj.get("sidecar", {}).get("records", []) if sj.get("found") else []
            break
        time.sleep(1)
    tgt = [r for r in recs
           if (r["locator"]["text_quote"] or "").replace(chr(10), "").replace(" ", "")
           and ((r["locator"]["text_quote"].replace(chr(10), "").replace(" ", "")
                 in REPEAT_A) or (REPEAT_A in r["locator"]["text_quote"]))]
    return (tgt[-1] if tgt else None), len(recs)


def _drag_current_and_verify(page, win_hwnd3, oracle_scan, sid3, base_count,
                             turn=False):
    """当前可视首行 → 真实拖选 → 新记录 oracle 核验（任意段，非目标句专用；
    red3 教训：scroll-redrag 翻页后目标句在前方页，前向 walk 永不回头——
    几何门一律用当前位置，不依赖句位）。turn=True 时先翻页（next() 直到首
    行文本变化≤4轮——拖选页可能是章节尾页，next() 空转复选同段被去重
    green6 实测）；拖选前补一次完整 down+up 冲刷遗留鼠标捕获（t04 教训，
    green6 hide-show 空选区实证）。返回 (ok, note, new_base)。"""
    def _first():
        for f in page.frames:
            try:
                fl_ = f.evaluate(_JS_FIRST_LINE)
            except Exception:
                fl_ = None
            if fl_:
                return fl_
        return None
    if turn:
        fl0 = _first()
        for _ in range(4):
            try:
                page.evaluate("() => window.__probe.view.renderer.next()")
            except Exception:
                pass
            page.wait_for_timeout(1200)
            fl1 = _first()
            if fl1 and (fl0 is None or fl1["text"] != fl0["text"]):
                break
            fl0 = fl1
    fl = _first()
    if not fl:
        return False, "no visible line", base_count
    if fl.get("width", 0) < 40:
        return False, f"degenerate line box w={fl.get('width')}", base_count
    popup = _find_popup_hwnd()
    if not popup:
        return False, "popup window gone", base_count
    rect = _win_rect(popup)
    vw = page.evaluate("() => window.innerWidth")
    scale = rect[2] / max(1, vw)
    fx = rect[0] + fl["x"] * scale + 4
    fy = rect[1] + (fl["y"] + fl["height"] * 0.5) * scale
    _send_mouse(fx, fy, True)
    time.sleep(0.08)
    _send_mouse(fx, fy, False)
    time.sleep(0.6)
    sel, err = _drag_line(page, rect, fl, win_hwnd3)
    # 持续轮询到 oracle 通过或超时。认领口径（dpi5 教训：纯计数 delta 会被
    # 乱序/先行到达的记录吸收）——候选 = oracle 通过 且【quote 与本次 CDP
    # 选区逐字一致（去空白）或 为 base 之后的新记录】；中间态跨栏拼接记录
    # （oracle 拒）自然过滤。
    sel_flat = (sel or "").replace(chr(10), "").replace(" ", "")
    t0 = time.monotonic()
    ok = False
    note = f"sel={str(sel)[:20]!r} err={err}"
    recs2 = []
    # 45s：adapter 回传 = 400ms 去抖 + countOccurrences 全书 createDocument
    # 扫描——DPI 切换/多章装载后实测晚到 20-30s（dpi4 sidecar 实证）。
    while time.monotonic() - t0 < 45 and not ok:
        sj = _http("GET", f"http://127.0.0.1:17827/api/probe/locators?session_id={sid3}")
        recs2 = sj.get("sidecar", {}).get("records", []) if sj.get("found") else []
        for idx, r in enumerate(recs2):
            q = (r["locator"]["text_quote"] or "").replace(chr(10), "").replace(" ", "")
            if not q or (REPEAT_A_MARKER in q):
                continue  # 目标句记录由专用门核验，这里要新段
            if idx < base_count and not (sel_flat and q == sel_flat):
                continue  # 旧记录且非本次选区
            vq = oracle_scan.verify_quote(r["locator"]["text_quote"],
                                          int(r["locator"]["occurrence"]))
            if vq.get("ok"):
                ok = True
                how = "sel-exact" if (sel_flat and q == sel_flat) else "new-record"
                note += f" [{how}] quote={q[:14]!r} oracle_ok pos={vq.get('position')}"
                break
        time.sleep(1.5 if recs2 else 1)
    return ok, note, max(base_count, len(recs2))


def _run_t05_gates(out_dir, mcp3, sid3, win_hwnd3, oracle_scan, results,
                   base_count):
    """T-05 扩展门：字体重排/滚动重拖/遮挡/隐藏展示/系统无障碍/键盘访问。
    在 resize-follow 之后执行（窗口已 MoveWindow 至 1400x1300@100,100）。"""
    popup = _find_popup_hwnd()
    if not popup:
        results("N-05.popup-found", "FAIL",
                "AutoUIDocSurfacePopup window not visible after resize")
        return
    popup_rect = _win_rect(popup)
    results("N-05.popup-found", "PASS",
            f"GetWindowRect={popup_rect}")
    pw5, browser5, page5 = _cdp_engine_page(sid3, cdp_port=9335)
    if page5 is None:
        results("N-05", "FAIL", "engine page not reachable via CDP for T-05 gates")
        if browser5:
            browser5.close()
        if pw5:
            pw5.stop()
        return

    def close_cdp():
        try:
            browser5.close()
            pw5.stop()
        except Exception:
            pass

    try:
        # ── N-05.font-reflow：真实字号重排（章节 body font-size 翻倍）→
        # 行盒位移 → 新几何上真实拖选重命中目标原文 ──
        lb0 = _measure_target_line(page5)
        if not lb0:
            results("N-05.font-reflow", "FAIL", "target line never visible")
            return
        frame_t = None
        for f in page5.frames:
            try:
                if REPEAT_A_MARKER in f.content():
                    frame_t = f
                    break
            except Exception:
                continue
        if frame_t is None:
            results("N-05.font-reflow", "FAIL", "target frame lost")
            return
        frame_t.evaluate("() => { document.body.style.fontSize = '200%'; }")
        page5.wait_for_timeout(2000)
        lb1 = _measure_target_line(page5)
        if not lb1:
            results("N-05.font-reflow", "FAIL", "target line lost after reflow")
            return
        moved = (abs(lb1["y"] - lb0["y"]) > 4 or abs(lb1["x"] - lb0["x"]) > 4
                 or abs(lb1["width"] - lb0["width"]) > 4)
        results("N-05.font-reflow.reflowed", "PASS" if moved else "FAIL",
                f"before=({lb0['x']:.0f},{lb0['y']:.0f},{lb0['width']:.0f}) "
                f"after=({lb1['x']:.0f},{lb1['y']:.0f},{lb1['width']:.0f})")
        if not moved:
            return
        popup_rect = _win_rect(_find_popup_hwnd()) if _find_popup_hwnd() else popup_rect
        sel, err = _drag_line(page5, popup_rect, lb1, win_hwnd3)
        rec, n_recs = _poll_target_record(sid3, base_count)
        ok = bool(sel) and rec is not None
        if ok:
            vq = oracle_scan.verify_quote(rec["locator"]["text_quote"],
                                          int(rec["locator"]["occurrence"]))
            ok = bool(vq.get("ok"))
            note = f"sel={str(sel)[:24]!r} occ={rec['locator']['occurrence']} oracle_ok={vq.get('ok')}"
        else:
            note = f"sel={str(sel)[:24]!r} err={err} recs={n_recs}"
        results("N-05.font-reflow.redrag", "PASS" if ok else "FAIL", note)
        if not ok:
            return
        base_count = n_recs

        # ── N-05.scroll-redrag：CDP 翻页（许可口径：CDP 用于翻页/只读观察，
        # 非代选）→ 内容重定位断言（首可视行文本必须变化）→ 真实拖选可视
        # 新段 → 独立 oracle 逐字/位次核验。键盘翻页路径归 N-06.keyboard。──
        def _first_line():
            for f in page5.frames:
                try:
                    fl_ = f.evaluate(_JS_FIRST_LINE)
                except Exception:
                    fl_ = None
                if fl_:
                    return fl_
            return None
        def _loc():
            try:
                return page5.evaluate(
                    "() => { const l = window.__probe.view.lastLocation;"
                    " return l ? (l.cfi + '|' + (l.pageItem ? l.pageItem.fraction : '')) : null; }")
            except Exception:
                return None
        loc0 = _loc()
        turned = False
        for _ in range(4):
            page5.evaluate("() => window.__probe.view.renderer.next()")
            page5.wait_for_timeout(1200)
            if _loc() != loc0:
                turned = True
                break
        if not turned:
            results("N-05.scroll-redrag", "FAIL",
                    f"view never relocated after 4 page turns (cfi stuck at {str(loc0)[:40]!r})")
        else:
            ok, note, base_count = _drag_current_and_verify(
                page5, win_hwnd3, oracle_scan, sid3, base_count)
            results("N-05.scroll-redrag", "PASS" if ok else "FAIL",
                    f"turned={turned} {note}")

        # ── N-06.uia-content：系统 UIA 树（PowerShell UIAutomationClient，
        # 屏读同源 API）从弹出窗定位正文文本——非 DOM ARIA、非 CDP ──
        _run_n06_uia(popup, out_dir, results)

        # ── N-06.keyboard-operate：UIA 焦点操作入文档 + 真实键盘翻页往返 ──
        _run_n06_keyboard(popup, out_dir, page5, results)

        # ── N-05.occlusion：真实 topmost 遮挡窗覆盖弹出窗 → 像素取证 →
        # 撤除 → 内容恢复（像素）+ 真实拖选当前可视段重命中 ──
        popup_rect = _win_rect(popup)
        cx = popup_rect[0] + popup_rect[2] * 0.5
        cy = popup_rect[1] + popup_rect[3] * 0.5
        p_before = _screen_pixel(cx, cy)
        # 遮挡前先跳 ch3：遮挡拖选位置与 ch1 前向路径（scroll-redrag）永不
        # 相交——同选区重复选择被消费端去重（green10 实测 14s 零记录）。
        try:
            page5.evaluate("() => window.__probe.view.goTo(2)")
        except Exception:
            pass
        page5.wait_for_timeout(1500)
        ov, br = _overlay_window(popup_rect[0], popup_rect[1],
                                 popup_rect[2], popup_rect[3])
        time.sleep(1.2)
        p_during = _screen_pixel(cx, cy)
        covered = p_during == (255, 0, 0)  # COLORREF 低字节=R → 红=(255,0,0)
        _drop_overlay(ov, br)
        time.sleep(1.5)
        p_after = _screen_pixel(cx, cy)
        restored = p_after != (255, 0, 0)
        results("N-05.occlusion.cover", "PASS" if covered else "FAIL",
                f"before={p_before} during={p_during} after={p_after} (occluder red)")
        if restored and not covered:
            # 覆盖失败：occluder 没盖住（z 序/几何问题）——门失败，不继续。
            results("N-05.occlusion.redrag", "FAIL",
                    "occluder did not cover the popup; redrag meaningless")
        else:
            # 翻一页取新段——同段重复选择被消费端去重（green3 实测 new=0）。
            ok, note, base_count = _drag_current_and_verify(
                page5, win_hwnd3, oracle_scan, sid3, base_count, turn=True)
            results("N-05.occlusion.redrag", "PASS" if ok else "FAIL",
                    f"restored={restored} {note}")

        # ── N-05.hide-show：MCP press 断开表面 → url 空路径 → 弹出窗必须
        # 真隐藏（真值=_find_popup_hwnd 查无+像素非内容）；重连 → 再现 +
        # 真实拖选重命中 ──
        snap = _mcp_text(mcp3, "autoui_snapshot")
        mb = re.search(r'button #(\S+) "断开表面"', snap)
        if not mb:
            results("N-05.hide-show", "FAIL", "Disconnect button not in MCP tree")
            return
        _mcp_text(mcp3, "autoui_action", {"element_id": mb.group(1), "action": "press"})
        time.sleep(2.0)
        gone = _find_popup_hwnd() is None
        cx = popup_rect[0] + popup_rect[2] * 0.5
        cy = popup_rect[1] + popup_rect[3] * 0.5
        p_hidden = _screen_pixel(cx, cy)
        results("N-05.hide-show.hidden", "PASS" if gone else "FAIL",
                f"popup_visible={not gone} pixel_at_center={p_hidden}")
        if not gone:
            # 弹出窗仍可见 = url 空路径未真隐藏（宿主接缝缺陷——修复前红）。
            results("N-05.hide-show", "FAIL",
                    "popup window still visible with empty surface url")
            return
        mc = re.search(r'button #(\S+) "连接会话"', _mcp_text(mcp3, "autoui_snapshot"))
        if not mc:
            results("N-05.hide-show", "FAIL", "Connect button not in MCP tree")
            return
        act = _mcp_text(mcp3, "autoui_action", {"element_id": mc.group(1), "action": "press"})
        if "status: ok" not in act:
            results("N-05.hide-show", "FAIL", "Connect press failed: " + act[:80])
            return
        back = None
        for _ in range(20):
            back = _find_popup_hwnd()
            if back:
                break
            time.sleep(1)
        if not back:
            results("N-05.hide-show", "FAIL", "popup did not re-appear after Connect (20s)")
            return
        time.sleep(2.5)
        rect_show = _win_rect(back)
        p_back = _screen_pixel(rect_show[0] + rect_show[2] * 0.5,
                               rect_show[1] + rect_show[3] * 0.5)
        results("N-05.hide-show.reshow", "PASS",
                f"rect={rect_show} pixel={p_back}")
        page5 = None
        # 双 sync_playwright 实例在 py3.14 冲突（asyncio loop 错误，green3
        # 实测）——先关 browser5 再开 page6 的连接。
        close_cdp()
        pw6, browser6, page6 = _cdp_engine_page(sid3, cdp_port=9335, deadline=45)
        if page6 is None:
            results("N-05.hide-show.redrag", "FAIL", "engine page lost after reshow")
            if browser6:
                browser6.close()
            if pw6:
                pw6.stop()
            return
        ok, note, base_count = _drag_current_and_verify(
            page6, win_hwnd3, oracle_scan, sid3, base_count, turn=True)
        results("N-05.hide-show.redrag", "PASS" if ok else "FAIL", note)

        # ── N-05.dpi-change（交互门，PROBE_DPI_INTERACTIVE=1 才执行）：
        # 用户经系统设置切换显示缩放 → 驱动检测 → 弹出窗/内容随新 DPI →
        # 真实拖选重命中；恢复后复验。预算语义：用户节奏单独计时（检测
        # 600s+恢复 600s），不计入 600s 自动链预算——计划 §5.2 语义修订。──
        if os.environ.get("PROBE_DPI_INTERACTIVE") == "1":
            _run_dpi_gate(win_hwnd3, page6, sid3, oracle_scan, base_count, results)
        else:
            results("N-05.dpi-change", "not_run",
                    "interactive gate: rerun with PROBE_DPI_INTERACTIVE=1 "
                    "(user-assisted display-scale change, 600s windows)")
        # page6 的 CDP 连接在 DPI 门用完后再关（dpi2 实测：先关后用=
        # "Event loop is closed" 崩溃）。
        try:
            browser6.close()
            pw6.stop()
        except Exception:
            pass
    finally:
        close_cdp()


def _run_n06_uia(popup, out_dir, results):
    """N-06.uia-content：系统 UIA（PowerShell UIAutomationClient）从弹出窗
    HWND 走系统树，定位正文文本（目标句片段）。Chromium 可达性按需激活——
    UIA 客户端走查即触发 WM_GETOBJECT 路径；样本树同时落盘供诊断。"""
    frag = "琥珀色的狐狸"
    ps1 = os.path.join(out_dir, "n06-uia.ps1")
    out_json = os.path.join(out_dir, "n06-uia.json")
    with open(ps1, "w", encoding="utf-8-sig") as f:
        f.write(_UIA_PS1)
    found = False
    note = ""
    r = None
    for attempt in range(3):
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-File", ps1, "-Hwnd", str(popup), "-Fragment", frag,
                 "-Out", out_json],
                capture_output=True, encoding="utf-8", errors="replace", timeout=180)
        except subprocess.TimeoutExpired:
            results("N-06.uia-content", "GAP", "UIA walk timed out (180s)")
            return
        try:
            j = json.loads(open(out_json, encoding="utf-8-sig").read())
            found = bool(j.get("hit"))
        except Exception:
            found = False
        if found:
            break
        time.sleep(3)  # 可达性树激活/装载时序波动（green8 实测 29 节点无正文）
    note = f"rc={r.returncode if r else -1} attempt={attempt + 1}"
    if os.path.exists(out_json):
        try:
            j = json.loads(open(out_json, encoding="utf-8-sig").read())
            hit = j.get("hit")
            found = bool(hit)
            chain = " <- ".join(f"{c.get('c')}:{c.get('t')}"
                                for c in (j.get("chain") or [])[:6])
            note += f" nodes={j.get('count')} hit={json.dumps(hit, ensure_ascii=False)[:120]} chain={chain[:140]}"
            if not found and j.get("error"):
                note += " err=" + str(j.get("error"))[:80]
        except Exception as e:
            note += " parse:" + repr(e)[:60]
    else:
        note += " stderr=" + (r.stderr or "")[:120]
    results("N-06.uia-content", "PASS" if found else "FAIL", note)


def _run_n06_keyboard(popup, out_dir, page5, results):
    """N-06.keyboard-operate：UIA SetFocus 操作文档元素（系统树操作）→
    焦点核验（GUI 线程焦点落在弹出窗子树）→ 真实 ArrowRight/Left 翻页往返
    （CDP lastLocation 为页位真值）。"""
    out_json = os.path.join(out_dir, "n06-uia-focus.json")
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", os.path.join(out_dir, "n06-uia.ps1"), "-Hwnd", str(popup),
             "-Fragment", "", "-Out", out_json, "-Mode", "focus"],
            capture_output=True, encoding="utf-8", errors="replace", timeout=180)
    except subprocess.TimeoutExpired:
        results("N-06.keyboard-operate", "GAP", "UIA focus walk timed out (180s)")
        return
    focus_el = None
    try:
        j = json.loads(open(out_json, encoding="utf-8-sig").read())
        focus_el = j.get("hit")
        uia_err = j.get("error")
        uia_count = j.get("count")
        uia_sample = (j.get("sample") or [])[:6]
    except Exception as e:
        uia_err, uia_count, uia_sample = repr(e)[:80], None, []
    focus_path = "uia"
    if not focus_el:
        # 回退：真实点击文档可视区（真实输入把焦点送进内容——用户自然路径）。
        focus_path = "real-click-fallback"
        pr = _win_rect(popup)
        fx = pr[0] + pr[2] * 0.5
        fy = pr[1] + pr[3] * 0.5
        _send_mouse(fx, fy)
        time.sleep(0.2)
        _send_mouse(fx, fy, down=True)
        time.sleep(0.08)
        _send_mouse(fx, fy, down=False)
        time.sleep(0.8)
    # 焦点核验：GUI 线程焦点必须落在弹出窗子树（系统焦点 ≠ 仅 CDP 断言）。
    class GUIINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("flags", ctypes.c_uint),
                    ("hwndActive", ctypes.c_void_p), ("hwndFocus", ctypes.c_void_p),
                    ("hwndCapture", ctypes.c_void_p), ("hwndMenuOwner", ctypes.c_void_p),
                    ("hwndMoveSize", ctypes.c_void_p), ("hwndCaret", ctypes.c_void_p),
                    ("rcCaret", ctypes.wintypes.RECT)]
    time.sleep(1.0)
    gi = GUIINFO()
    gi.cbSize = ctypes.sizeof(gi)
    user32.GetGUIThreadInfo(0, ctypes.byref(gi))
    fh = gi.hwndFocus or 0
    in_popup = bool(fh) and bool(user32.IsChild(popup, fh))
    results("N-06.keyboard-operate.uia-focus", "PASS" if in_popup else "FAIL",
            f"path={focus_path} el={json.dumps(focus_el, ensure_ascii=False)[:70]} "
            f"hwndFocus={fh:#x} in_popup_tree={in_popup}")
    if not in_popup:
        return
    # 真实键盘翻页往返：ArrowRight → 页位变化；ArrowLeft → 回到原页位。
    def _loc():
        try:
            return page5.evaluate(
                "() => { const l = window.__probe.view.lastLocation;"
                " return l ? (l.cfi + '|' + (l.pageItem ? l.pageItem.fraction : '')) : null; }")
        except Exception:
            return None
    loc0 = _loc()
    _send_key(0x27)  # ArrowRight
    time.sleep(1.5)
    loc1 = _loc()
    _send_key(0x25)  # ArrowLeft
    time.sleep(1.5)
    loc2 = _loc()
    turned = loc1 is not None and loc0 is not None and loc1 != loc0
    back = loc2 == loc0
    results("N-06.keyboard-operate", "PASS" if (turned and back) else "FAIL",
            f"loc0={str(loc0)[:36]} right={str(loc1)[:36]} turned={turned} "
            f"back={back} (real ArrowRight/Left)")


def _run_dpi_gate(win_hwnd3, page6, sid3, oracle_scan, base_count, results):
    """N-05.dpi-change（交互门）：用户经系统设置切换显示缩放 → 驱动自动
    检测（每秒轮询 iced 窗 DPI，150s 窗口）→ 弹出窗/内容随新 DPI（真值：
    GetWindowRect vs CDP innerWidth×新scale）→ 真实拖选重命中目标原文 →
    提示恢复 → 复验。预算语义：用户节奏单独计时，见计划 §5.2 语义修订。"""
    def _popup():
        h = _find_popup_hwnd()
        return (h, _win_rect(h)) if h else (None, None)

    dpi0 = user32.GetDpiForWindow(win_hwnd3) or 96
    # 检测窗 600s：用户节奏（AskUserQuestion 协调往返 + 设置操作）远超短窗
    # ——首跑 150s 实测超时（用户已切、窗口先关）。预算语义修订见计划 §5.2。
    print(f">>> N-05.dpi-change: 请在 设置>系统>屏幕 将显示缩放改为其他档位"
          f"（当前 DPI={dpi0}，600 秒内）<<<", flush=True)
    dpi1 = None
    t0 = time.monotonic()
    while time.monotonic() - t0 < 600:
        d = user32.GetDpiForWindow(win_hwnd3)
        if d != dpi0:
            dpi1 = d
            break
        time.sleep(1)
    if not dpi1:
        results("N-05.dpi-change", "GAP",
                f"display scale not changed within 600s (dpi stayed {dpi0})")
        return
    time.sleep(5)  # winit WM_DPICHANGED 重排 + doc-surface sync + WebView2 栅格化
    pop, prect = _popup()
    vw = page6.evaluate("() => window.innerWidth")
    vh = page6.evaluate("() => window.innerHeight")
    exp_w = (vw * dpi1 / 96.0) if vw else 0
    tracked = bool(pop) and prect and abs(prect[2] - exp_w) <= 6
    results("N-05.dpi-change.track", "PASS" if tracked else "FAIL",
            f"dpi {dpi0}->{dpi1} popup={prect} innerWidth={vw} expected_w={exp_w:.0f}")
    if not tracked:
        return
    # 当前位置拖选 + oracle（位置依赖教训：视口可在任意章——dpi3 实测 ch3
    # 上目标句前向 walk 永不达；track 门已证几何跟随，此处证输入重命中）。
    ok, note, base_count = _drag_current_and_verify(
        page6, win_hwnd3, oracle_scan, sid3, base_count, turn=True)
    results("N-05.dpi-change.redrag", "PASS" if ok else "FAIL", note)
    print(">>> 请恢复显示缩放回原档位（600 秒内）<<<", flush=True)
    t0 = time.monotonic()
    restored = False
    while time.monotonic() - t0 < 600:
        if user32.GetDpiForWindow(win_hwnd3) == dpi0:
            restored = True
            break
        time.sleep(1)
    if not restored:
        results("N-05.dpi-change.restore", "GAP", "scale not restored within 600s")
        return
    time.sleep(5)
    pop2, prect2 = _popup()
    back = bool(pop2) and prect2 and abs(prect2[2] - vw * dpi0 / 96.0) <= 6
    results("N-05.dpi-change.restore", "PASS" if back else "FAIL",
            f"popup={prect2} expected_w={vw * dpi0 / 96.0:.0f}")


_UIA_PS1 = r"""param(
    [long]$Hwnd,
    [string]$Fragment,
    [string]$Out,
    [string]$Mode = 'find'
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$root = [System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]$Hwnd)
$result = [ordered]@{
    root = @{ name = $root.Current.Name; class = $root.Current.ClassName
              type = $root.Current.ControlType.ProgrammaticName }
    count = 0
    hit = $null
    chain = @()
    sample = @()
    error = $null
}
function ElemInfo($el) {
    $name = ''
    $cls = ''
    $typ = ''
    $kbd = $false
    try { $name = $el.Current.Name } catch {}
    try { $cls = $el.Current.ClassName } catch {}
    try { $typ = $el.Current.ControlType.ProgrammaticName } catch {}
    try { $kbd = $el.Current.IsKeyboardFocusable } catch {}
    @{ n = $name; c = $cls; t = $typ; k = $kbd }
}
try {
    if ($Mode -eq 'focus') {
        # 找第一个可键入焦点/文档类元素并 SetFocus（系统树操作）。
        $walker = [System.Windows.Automation.TreeWalker]::ControlViewWalker
        $stack = [System.Collections.Stack]::new()
        $stack.Push(@($root, 0))
        while ($stack.Count -gt 0 -and $result.count -lt 2500) {
            $entry = $stack.Pop()
            $el = $entry[0]; $depth = $entry[1]
            $result.count++
            $info = ElemInfo $el
            # ProgrammaticName 形如 ControlType.Document（red3 实测误写
            # '*DocumentControl*' 永不命中）——文本/文档容器均可作焦点锚。
            $isDoc = ($info.t -like '*Document*')
            if (($info.k -and $depth -gt 1) -or $isDoc) {
                try {
                    $el.SetFocus()
                    $result.hit = @{ c = $info.c; t = $info.t; n = $info.n.Substring(0, [Math]::Min(60, $info.n.Length)); k = $info.k }
                } catch { $result.error = $_.Exception.Message }
                break
            }
            if ($result.sample.Count -lt 40) { $result.sample += @{ d = $depth; t = $info.t; c = $info.c; k = $info.k } }
            $child = $walker.GetFirstChild($el)
            while ($null -ne $child) {
                $stack.Push(@($child, $depth + 1))
                $child = $walker.GetNextSibling($child)
            }
        }
    } else {
        $walker = [System.Windows.Automation.TreeWalker]::ControlViewWalker
        $stack = [System.Collections.Stack]::new()
        $stack.Push(@($root, 0))
        while ($stack.Count -gt 0 -and $result.count -lt 2500) {
            $entry = $stack.Pop()
            $el = $entry[0]; $depth = $entry[1]
            $result.count++
            $info = ElemInfo $el
            if ($result.sample.Count -lt 150) {
                $result.sample += @{ d = $depth; t = $info.t; c = $info.c
                                     n = $info.n.Substring(0, [Math]::Min(60, $info.n.Length)) }
            }
            if ($info.n -and $info.n.Contains($Fragment)) {
                $result.hit = @{ c = $info.c; t = $info.t
                                 n = $info.n.Substring(0, [Math]::Min(120, $info.n.Length)) }
                $cur = $el
                while ($null -ne $cur) {
                    $ci = ElemInfo $cur
                    $result.chain += @{ c = $ci.c; t = $ci.t }
                    if ($result.chain.Count -ge 12) { break }
                    $cur = $walker.GetParent($cur)
                }
                break
            }
            $child = $walker.GetFirstChild($el)
            while ($null -ne $child) {
                $stack.Push(@($child, $depth + 1))
                $child = $walker.GetNextSibling($child)
            }
        }
    }
} catch { $result.error = $_.Exception.Message }
$result | ConvertTo-Json -Depth 5 | Set-Content -Path $Out -Encoding UTF8"""

