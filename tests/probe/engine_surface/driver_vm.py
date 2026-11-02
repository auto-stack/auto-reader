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
import time
import urllib.request

from driver_vue import Instance  # 复用实例管理/导入面
from driver_vue import http as _http

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(HERE, "app")
ENGINE_REVISION = "foliate-js@3d794195"

# 目标句前缀（verify_engine_surface.REPEAT_A 同源常量；第 2 处 = ch1 para7）。
REPEAT_A_MARKER = "探针重复句甲"

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


def _cdp_engine_page(marker, deadline=30):
    """CDP 找 native-host 页并等待引擎装载；返回 (page, engine)。"""
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
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
    """翻页至目标句 → 真实 SendInput 拖选 → sidecar/oracle 核验。"""
    wpx, hpx, ox, oy = rect
    # 目标句所在 frame/para（跨 iframe 搜索，026 vue 臂同纪律）。
    found_frame = None
    t0 = time.monotonic()
    while time.monotonic() - t0 < 15 and not found_frame:
        for f in page.frames:
            try:
                if REPEAT_A_MARKER in f.content():
                    found_frame = f
                    break
            except Exception:
                continue
        if not found_frame:
            time.sleep(1)
    if not found_frame:
        results(tag, "FAIL", "target text not in any frame (15s)")
        return None
    loc = found_frame.locator(f"text={REPEAT_A_MARKER}").last
    loc.wait_for(state="attached", timeout=10000)
    vw0 = page.evaluate("() => window.innerWidth")
    para_box = None
    for _ in range(12):
        try:
            para_box = loc.bounding_box()
        except Exception:
            para_box = None
        # 必须真实入视口（分栏排版下目标可能整列停在视口右侧——
        # x=innerWidth 处 size 合法但不可见，拖选必落空：t03 实测）。
        if (para_box and para_box.get("width", 0) > 40
                and para_box.get("height", 0) > 8
                and para_box["x"] >= -4
                and para_box["x"] + para_box["width"] <= vw0 + 4):
            break
        page.evaluate("() => window.__probe.view.renderer.next()")
        page.wait_for_timeout(700)
    if not para_box:
        results(tag, "FAIL", "target paragraph never visible (12 pages)")
        return None
    results(tag + ".target-visible", "PASS",
            f"2nd-occurrence para on page ({int(para_box['width'])}x{int(para_box['height'])} css)")

    # css → 宿主屏幕物理坐标：视口 = 子表面，比例 = wpx/innerWidth。
    vw = page.evaluate("() => window.innerWidth")
    scale = wpx / max(1, vw)
    cpt = ctypes.wintypes.POINT(0, 0)
    user32.ClientToScreen(win_hwnd, ctypes.byref(cpt))
    bx0 = cpt.x + ox + para_box["x"] * scale
    by0 = cpt.y + oy + para_box["y"] * scale
    bw = para_box["width"] * scale
    bh = para_box["height"] * scale
    # 逐点 hit-test 守卫（T-00 教训：覆盖层/误窗必须具名失败）。
    _, cls0 = _hit_window(bx0 + bw * 0.3, by0 + bh * 0.4)
    guard = ("Chrome" in cls0) or ("WRY" in cls0.upper())
    results(tag + ".hit-guard", "PASS" if guard else "FAIL", "hit=" + cls0)
    if not guard:
        return None
    _force_foreground(win_hwnd)
    time.sleep(0.5)
    fg_ok = user32.GetForegroundWindow() == win_hwnd
    results(tag + ".foreground", "PASS" if fg_ok else "GAP",
            "fg==hwnd:" + str(fg_ok))
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
    time.sleep(3)
    return True


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

        env = {"PROBE_DATA_DIR": data_dir, "PROBE_ASSETS_DIR": assets_dir,
               "PROBE_PUBLIC_BASE": "http://127.0.0.1:17827",
               "AUTO_DOC_SURFACE_DEBUG": "1",
               "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS": "--remote-debugging-port=9333",
               "AUTO_VM_WINDOW": "900x700,40,40"}
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
        rec = recs[-1]
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
        ok_disk = os.path.exists(disk) and quote in open(disk, encoding="utf-8").read()
        results("N-02.sidecar-disk", "PASS" if ok_disk else "FAIL", disk)
        n_saved = len(recs)

        # ── N-03：正常关闭 → 新进程冷恢复 ──
        cons.stop()
        time.sleep(2)
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
        pw, browser, page2 = _cdp_engine_page(sid2)
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
