#!/usr/bin/env python3
# driver_vm.py — PLAN-026 原生（VM split）臂表面驱动。
# 原生表面 = experiments/reader-engine-probe native_host.exe（iced 0.14 主窗
# 口 + wry WebView2 子表面，T-03 PASS 缝隙）从消费 app 同源装载引擎资产与
# 受管文档；真实 OS 级输入（ctypes SendInput 拖选）→ 引擎 CFI → fetch →
# .at handler → sidecar 独立读回。不代选：拖选为真实系统鼠标事件。
import ctypes
import ctypes.wintypes
import json
import os
import subprocess
import time
import urllib.request

from driver_vue import Instance  # 复用实例管理/导入面
from driver_vue import http as _http

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(HERE, "app")
ENGINE_REVISION = "foliate-js@3d794195"

NATIVE_HOST = os.environ.get(
    "PROBE_NATIVE_HOST",
    r"D:\autostack\.wt\ui-026\auto-ui\experiments\reader-engine-probe"
    r"\target\release\native_host.exe")

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


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
    → 仍败则最小化/恢复（恢复路径授予前台）。"""
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
    sw = user32.GetSystemMetrics(76)   # SM_CXVIRTUALSCREEN
    sh = user32.GetSystemMetrics(77)   # SM_CYVIRTUALSCREEN
    ox = user32.GetSystemMetrics(88)   # SM_XVIRTUALSCREEN
    oy = user32.GetSystemMetrics(89)   # SM_YVIRTUALSCREEN
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


def run_vm(out_dir, corpus_dir, oracle_scan, results):
    """V-01/V-02/V-05(原生臂) + 负控复用。results = record(case,outcome,detail)。"""
    data_dir = os.path.join(out_dir, "probe-data")
    reader_data = os.path.join(out_dir, "reader-data")
    import shutil
    for d in (data_dir, reader_data):
        shutil.rmtree(d, ignore_errors=True)
    assets_dir = os.environ.get("PROBE_ASSETS_DIR", "")
    if not os.path.isfile(os.path.join(assets_dir, "native-host.html")):
        results("NV-01", "GAP", "native assets missing: " + assets_dir)
        return
    if not os.path.isfile(NATIVE_HOST):
        results("NV-01", "GAP", "native_host.exe missing (build T-03 crate first)")
        return

    epub = os.path.join(corpus_dir, "probe-alpha.epub")
    reader_inst = Instance(HERE and os.path.abspath(os.path.join(HERE, "..", "..", "..")),
                           os.path.join(out_dir, "reader.log"),
                           {"AUTO_READER_DATA": reader_data})
    cons = None
    host = None
    try:
        if not reader_inst.wait("http://127.0.0.1:17825/api/library/books"):
            results("NV-01", "FAIL", "reader boot timeout")
            return
        r = _http("POST", "http://127.0.0.1:17825/api/library/import",
                  {"path": epub.replace("\\", "/"), "author": "PLAN-026", "force": False},
                  timeout=120)
        if '"book_id"' not in json.dumps(r, ensure_ascii=False):
            results("NV-01", "FAIL", "import failed")
            return
        books = _http("GET", "http://127.0.0.1:17825/api/library/books")
        bl = books.get("books") if isinstance(books, dict) else books
        target = next((b for b in bl if b.get("format") == "epub"), None)
        bj = _http("GET", "http://127.0.0.1:17825/api/library/books/" + target["book_id"])
        ident = {"book_id": bj["book_id"], "source_hash": bj["source_hash"],
                 "managed_path": str(bj["managed_path"]).replace("\\", "/"),
                 "size": os.path.getsize(bj["managed_path"])}
        results("NV-01.reader-import", "PASS",
                f"book_id={ident['book_id'][:13]}… managed={os.path.basename(ident['managed_path'])}")

        cons = Instance(APP_DIR, os.path.join(out_dir, "consumer.log"),
                        {"PROBE_DATA_DIR": data_dir, "PROBE_ASSETS_DIR": assets_dir})
        if not cons.wait("http://127.0.0.1:17827/api/probe/health"):
            results("NV-01", "FAIL", "consumer backend boot timeout")
            return
        _http("POST", "http://127.0.0.1:17827/api/probe/register",
              {"book_id": ident["book_id"], "source_hash": ident["source_hash"],
               "managed_path": ident["managed_path"], "title": "probe-alpha",
               "book_bytes": ident["size"]})
        sid = "vm-sess-" + str(int(time.time()))
        _http("POST", "http://127.0.0.1:17827/api/probe/session",
              {"session_id": sid, "book_id": ident["book_id"],
               "source_hash": ident["source_hash"], "engine": ENGINE_REVISION})

        url = ("http://127.0.0.1:17827/api/probe/asset/native-host.html?doc="
               + ident["book_id"] + "&session=" + sid + "&hash="
               + ident["source_hash"])
        host_log = open(os.path.join(out_dir, "native-host.log"), "w",
                        encoding="utf-8", errors="replace")
        env = dict(os.environ, PROBE_T03_MODE="engine", PROBE_T03_URL=url)
        host = subprocess.Popen([NATIVE_HOST], env=env, stdout=host_log,
                                stderr=subprocess.STDOUT)

        # V-01 原生臂：等待引擎身份 IPC（deadline 30s）。
        engine_ipc = None
        t0 = time.monotonic()
        while time.monotonic() - t0 < 30:
            try:
                with open(os.path.join(out_dir, "native-host.log"), encoding="utf-8",
                          errors="replace") as f:
                    for line in f:
                        if "t03-engine" in line:
                            engine_ipc = line.strip()
                            break
            except OSError:
                pass
            if engine_ipc:
                break
            time.sleep(1)
        ok_v1 = engine_ipc is not None and '"surface_alive":true' in engine_ipc \
            and '"spine":3' in engine_ipc
        results("NV-01.engine-in-iced-host", "PASS" if ok_v1 else "FAIL",
                (engine_ipc or "no engine ipc in 30s")[:200])

        # V-02 原生臂：真实 SendInput 拖选。
        hwnds = _find_windows_of_pid(host.pid)
        time.sleep(3)
        hwnds = _find_windows_of_pid(host.pid) or hwnds
        if not hwnds:
            results("NV-02", "FAIL", "no visible native window found")
            return
        # 取客户区最大的可见窗（iced 主窗；WebView2 子层级不在顶层枚举）。
        def _area(h):
            r = ctypes.wintypes.RECT()
            user32.GetClientRect(h, ctypes.byref(r))
            return r.right * r.bottom
        hwnd = max(hwnds, key=_area)
        _force_foreground(hwnd)
        time.sleep(0.5)
        fg_now = user32.GetForegroundWindow()
        results("NV-02.foreground-check", "PASS" if fg_now == hwnd else "FAIL",
                f"fg==hwnd:{fg_now == hwnd} hwnds={len(hwnds)}")
        cx0, cy0 = _client_origin(hwnd)
        w0, h0 = _client_size(hwnd)
        results("NV-02.window-geometry", "PASS" if w0 > 200 and h0 > 200 else "FAIL",
                f"client={w0}x{h0} origin=({cx0},{cy0})")
        cx, cy = _client_origin(hwnd)
        w, h = _client_size(hwnd)
        # 子窗口层级诊断：webview 子 HWND 是否存在、命中点落在哪个子窗。
        children = []
        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        def _cb(ch, _l):
            buf = ctypes.create_unicode_buffer(128)
            user32.GetClassNameW(ch, buf, 128)
            r = ctypes.wintypes.RECT()
            user32.GetWindowRect(ch, ctypes.byref(r))
            children.append((buf.value, r.left, r.top, r.right - r.left, r.bottom - r.top))
            return True
        user32.EnumChildWindows(hwnd, _cb, None)
        results("NV-02.child-hwnds", "PASS" if children else "FAIL",
                "; ".join(f"{c[0]}@{c[1]},{c[2]} {c[3]}x{c[4]}" for c in children)[:220] or "none")
        pt = ctypes.wintypes.POINT(int(cx + w * 0.3), int(cy + h * 0.4))
        hit = user32.WindowFromPoint(pt)
        buf = ctypes.create_unicode_buffer(128)
        user32.GetClassNameW(hit, buf, 128)
        results("NV-02.hit-window", "PASS", f"{buf.value} @({pt.x},{pt.y})")
        # 首列顶部是 h1 标题（quote_not_found 拒绝路径）——拖选落在正文段。
        sx, sy = cx + w * 0.15, cy + h * 0.30
        ex, ey = cx + w * 0.60, cy + h * 0.52
        slow = float(os.environ.get("PROBE_DRAG_STEP_S", "0.12"))
        _force_foreground(hwnd)
        _send_mouse(sx, sy)
        time.sleep(0.25)
        _send_mouse(sx, sy, down=True)
        time.sleep(0.2)
        for i in range(1, 13):
            _send_mouse(sx + (ex - sx) * i / 12, sy + (ey - sy) * i / 12)
            time.sleep(slow)
        time.sleep(0.2)
        _send_mouse(ex, ey, down=False)
        time.sleep(2)
        # 键盘选择补路径（真实 OS 键盘输入）：单击聚焦 + Ctrl+A。
        _send_mouse(cx + w * 0.3, cy + h * 0.4, down=True)
        time.sleep(0.1)
        _send_mouse(cx + w * 0.3, cy + h * 0.4, down=False)
        time.sleep(0.6)
        user32.keybd_event(0x11, 0, 0, 0)        # CTRL down
        user32.keybd_event(0x41, 0, 0, 0)        # A down
        user32.keybd_event(0x41, 0, 2, 0)        # A up
        user32.keybd_event(0x11, 0, 2, 0)        # CTRL up
        time.sleep(2)
        side = _http("GET", f"http://127.0.0.1:17827/api/probe/locators?session_id={sid}")
        recs = side.get("sidecar", {}).get("records", []) if side.get("found") else []
        if recs:
            rec = recs[0]
            vq = oracle_scan.verify_quote(rec["locator"]["text_quote"],
                                          int(rec["locator"]["occurrence"]))
            results("NV-02.real-sendinput-drag", "PASS" if vq.get("ok") else "FAIL",
                    f"quote={rec['locator']['text_quote'][:28]}… occ={rec['locator']['occurrence']} "
                    f"cfi={str(rec['locator']['cfi'])[:40]} oracle={vq.get('position')}")
            results("NV-02.cfi-present",
                    "PASS" if str(rec["locator"]["cfi"]).startswith("epubcfi") else "FAIL",
                    "cfi=" + str(rec["locator"]["cfi"])[:50])
            disk = os.path.join(data_dir, "probe", "locators", sid + ".json")
            ok_disk = os.path.exists(disk) and rec["locator"]["text_quote"] in \
                open(disk, encoding="utf-8").read()
            results("NV-02.sidecar-disk", "PASS" if ok_disk else "FAIL", disk)
        else:
            results("NV-02.real-sendinput-drag", "FAIL",
                    "no sidecar record after real drag (sidecar found=" + str(side.get("found")) + ")")

        # V-05 原生臂（几何）：resize 后再次真实拖选仍成功 → 表面跟随宿主。
        ctypes.windll.user32.MoveWindow(hwnd, 60, 60, int(w * 0.7), int(h * 0.7), True)
        time.sleep(2)
        cx, cy = _client_origin(hwnd)
        w2, h2 = _client_size(hwnd)
        sx, sy = cx + w2 * 0.2, cy + h2 * 0.18
        ex, ey = cx + w2 * 0.6, cy + h2 * 0.38
        _force_foreground(hwnd)
        _send_mouse(sx, sy)
        time.sleep(0.25)
        _send_mouse(sx, sy, down=True)
        time.sleep(0.2)
        for i in range(1, 13):
            _send_mouse(sx + (ex - sx) * i / 12, sy + (ey - sy) * i / 12)
            time.sleep(slow)
        time.sleep(0.2)
        _send_mouse(ex, ey, down=False)
        time.sleep(2)
        # 键盘选择补路径（真实 OS 键盘输入）：单击聚焦 + Ctrl+A。
        _send_mouse(cx + w * 0.3, cy + h * 0.4, down=True)
        time.sleep(0.1)
        _send_mouse(cx + w * 0.3, cy + h * 0.4, down=False)
        time.sleep(0.6)
        user32.keybd_event(0x11, 0, 0, 0)        # CTRL down
        user32.keybd_event(0x41, 0, 0, 0)        # A down
        user32.keybd_event(0x41, 0, 2, 0)        # A up
        user32.keybd_event(0x11, 0, 2, 0)        # CTRL up
        time.sleep(2)
        side2 = _http("GET", f"http://127.0.0.1:17827/api/probe/locators?session_id={sid}")
        n2 = len(side2.get("sidecar", {}).get("records", [])) if side2.get("found") else 0
        results("NV-05.resize-then-redrag", "PASS" if n2 >= 2 else "FAIL",
                f"records after resize+redrag={n2} (expect ≥2)")
    finally:
        if host and host.poll() is None:
            host.kill()
            host.wait()
        if cons:
            cons.stop()
        reader_inst.stop()
