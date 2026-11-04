#!/usr/bin/env python3
"""auto-os/PLAN-059 theme-adoption counter-controls for 018-book-reader.

Legs (vue track, `auto run --server=vm`; frozen os-059 chain via env roots):

  A  explicit override track: AUTO_UI_THEME=dark -> Auto family dark applied:
     shell root #09090b exact; engine port readback theme=dark; foliate
     document html #1f2430 exact (READER-007 engine port consumption).
  B  OS-follow track: AUTO_UI_THEME unset -> light-OS machine boots light:
     shell root #ffffff exact; engine port readback theme=light.
  F  standalone follow track: AUTOOS_DESKTOP_CONFIG -> Solarized/dark policy:
     shell root #002b36 exact (Solarized dark token); engine derived dark.
  FB bad-digest candidate in config -> named rejection, shell stays legacy
     light (保旧); tool-host log carries the rejection line.
  FR reopen-to-latest: fix config to Auto/dark, restart -> shell #09090b
     (合同命名恢复路径"重开").
  S  explicit-beats-follow: sepia persisted via real UI picker on light boot,
     re-open under Solarized/dark follow -> shell dark + reading stays sepia
     (显式 override > follow), sepia engine color #f4ecd8 exact.

Business sentinels (all legs): imported corpus book (山月与潮声) visible on
the shelf; reading page engine loads (V-02 换肤不丢业务).

Original gates untouched (verify_standalone/verify_local/verify_epub/
verify_epub_product/auto test). Evidence: D:/autostack/plan-artifacts/
plan-059/auto-os/reader/ (never the user's real library).
"""

import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ART = r"D:\autostack\plan-artifacts\plan-059\auto-os\reader"
CORPUS = r"D:\autostack\plan-artifacts\plan-059\auto-os\corpus"
BOOK_TITLE = "山月与潮声"

# Official package tokens (vendor/themes 0.2.0, digest 9fa07742..bef838e)
AUTO_DARK_BG = "rgb(9, 9, 11)"
AUTO_LIGHT_BG = "rgb(255, 255, 255)"
SOLARIZED_DARK_BG = "rgb(0, 43, 54)"
ENGINE_DARK_BG = "rgb(31, 36, 48)"     # engine-adapter.js dark CSS
ENGINE_SEPIA_BG = "rgb(244, 236, 216)"  # engine-adapter.js sepia CSS

CHAIN_ENV = {
    "AUTO_LANG_ROOT": r"D:\autostack\.wt\os-059\auto-lang",
    "AUTO_WEB_ROOT": r"D:\autostack\.wt\os-059\auto-web",
    "AUTO_UI_TOOL_BIN": r"D:\autostack\.wt\os-059\auto-ui\target\debug\auto-ui-tool.exe",
    "AUTO_HTTP_STEP_BUDGET": "1000000000",
    "AUTO_HTTP_REQUEST_TIMEOUT_MS": "300000",
}
PW_ENV = {
    "PW_CHROMIUM": os.environ.get(
        "PW_CHROMIUM",
        r"C:\Users\zhaop\AppData\Local\ms-playwright\chromium-1248\chrome-win64\chrome.exe"),
}


def npx_cmd():
    return shutil.which("npx") or shutil.which("npx.cmd") or "npx"


def pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def http_json(url, method="GET", body=None, timeout=20):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        v = json.loads(r.read().decode())
    # .at 后端 JSON 字符串体可能双层编码（verify_standalone http() 同式）
    if isinstance(v, str) and v:
        v = json.loads(v)
    return v


def write_solarized_config(path, family="Solarized", mode="dark",
                           version="0.2.0",
                           digest="9fa07742dc68aa5377ae06cb2d966386002063f184c515b6c5dddf8a6bef838e"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        "theme_family: \"%s\"" % family,
        "theme_family_version: \"%s\"" % version,
        "theme_family_digest: \"%s\"" % digest,
        "theme_mode: \"%s\"" % mode,
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def boot(app_env_extra, data_dir, log_name):
    """Boot `auto run --server=vm` with frozen chain + leg env. Returns proc."""
    os.makedirs(data_dir, exist_ok=True)
    log_path = os.path.join(ART, log_name)
    logf = open(log_path, "w", encoding="utf-8", errors="replace")
    env = dict(os.environ, **CHAIN_ENV, **app_env_extra,
               AUTO_READER_DATA=data_dir)
    env.pop("AUTO_UI_THEME", None)
    env.pop("AUTOOS_DESKTOP_CONFIG", None)
    env.update(app_env_extra)
    proc = subprocess.Popen(
        [os.environ.get("AUTO_BIN",
                        r"D:\autostack\auto-man\target\debug\auto.exe"),
         "run", "--server=vm"],
        cwd=ROOT, env=env, stdout=logf, stderr=subprocess.STDOUT)
    proc.__logf = logf
    t0 = time.time()
    backend_up = False
    while time.time() - t0 < 300:
        if proc.poll() is not None:
            logf.close()
            raise RuntimeError(f"{log_name}: run exited early rc={proc.returncode}")
        if not backend_up:
            try:
                http_json("http://127.0.0.1:17825/api/library/books", timeout=3)
                backend_up = True
                print(f"  [*] backend up in {time.time()-t0:.0f}s", flush=True)
            except Exception:
                time.sleep(2)
                continue
        # front（vite）就绪后才交 spec（冷 gen 全量 install 时慢启动）
        try:
            with urllib.request.urlopen("http://localhost:17824/", timeout=3) as r:
                head = r.read(120).decode("utf-8", "replace")
                if "<html" in head.lower() or "<!doctype" in head.lower():
                    print(f"  [*] front up in {time.time()-t0:.0f}s", flush=True)
                    return proc
        except Exception:
            pass
        time.sleep(2)
    logf.close()
    raise RuntimeError(f"{log_name}: backend={backend_up} front not ready in 300s")


def run_spec(leg, env_expect, timeout=600):
    """Run the playwright theme spec against the live instance."""
    env = dict(os.environ, **PW_ENV, **env_expect)
    env.pop("AUTO_UI_THEME", None)
    env.pop("AUTOOS_DESKTOP_CONFIG", None)
    r = subprocess.run([npx_cmd(), "playwright", "test", "theme_059_ui.spec.ts"],
                       cwd=os.path.join(ROOT, "tests"), env=env,
                       capture_output=True, text=True, timeout=timeout,
                       encoding="utf-8", errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    with open(os.path.join(ART, f"spec-{leg}.log"), "w", encoding="utf-8") as f:
        f.write(out)
    return r.returncode, out


def import_corpus():
    imp = http_json("http://127.0.0.1:17825/api/library/import", "POST",
                    {"path": os.path.join(CORPUS, "product-alpha.epub"),
                     "author": "PLAN-059", "force": False}, timeout=120)
    # duplicate（S2 复用 data-S）= 明确提示复用，非失败——书架上能查到即成功
    lib = http_json("http://127.0.0.1:17825/api/library/books", timeout=20)
    found = any(b.get("title") == BOOK_TITLE for b in lib.get("books", []))
    print(f"  [*] import product-alpha: code={imp.get('code')} shelf_found={found}", flush=True)
    return bool(found)


class Mcp:
    """auto-ui-tool MCP client（music test_058 同式；VM 轨状态/截图面）。"""

    def __init__(self, port: int):
        self.url = f"http://127.0.0.1:{port}/mcp"
        self._id = 0

    def call(self, tool, args=None):
        self._id += 1
        req = json.dumps({"jsonrpc": "2.0", "id": self._id, "method": "tools/call",
                          "params": {"name": tool, "arguments": args or {}}}).encode()
        r = urllib.request.Request(self.url, data=req,
                                   headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(r, timeout=20) as resp:
            out = json.loads(resp.read().decode())
        return out.get("result", {})

    def state(self):
        return self.call("autoui_state").get("content", [{}])[0].get("text", "")

    def shot(self, name):
        raw = self.call("autoui_screenshot",
                        {"name": name, "baseline": False}).get("content", [{}])[0].get("text", "")
        low = raw.lower()
        if "saved to" in low:
            return raw[low.index("saved to") + 8:].lstrip(" :").replace("\\\\?\\", "").strip()
        return ""


def interior_pixel(png_path):
    from PIL import Image
    with Image.open(png_path) as im:
        rgb = im.convert("RGB")
        px = [rgb.getpixel((x, y)) for x in range(700, 706) for y in range(24, 30)]
    n = len(px)
    return tuple(round(sum(c[i] for c in px) / n) for i in range(3))


def boot_vm(app_env_extra, data_dir, log_name):
    """VM 轨 boot（007 verify_epub_product vm 同式：-r vm --no-merge -B）。

    返回 (proc, mcp_port)。standalone 跟随臂（AUTOOS_DESKTOP_CONFIG 400ms
    轮询）只武装 iced/VM 窗路径（auto-ui-runtime dynamic_build
    arm_standalone_follow）——vue 轨无此臂，故 F/FB/FR/S2 全走 VM 轨。
    """
    os.makedirs(data_dir, exist_ok=True)
    log_path = os.path.join(ART, log_name)
    logf = open(log_path, "w", encoding="utf-8", errors="replace")
    env = dict(os.environ, **CHAIN_ENV, **app_env_extra, AUTO_READER_DATA=data_dir,
               AUTO_VM_WINDOW="1000x720")
    env.pop("AUTO_UI_THEME", None)
    env.pop("AUTOOS_DESKTOP_CONFIG", None)
    env.update(app_env_extra)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        mcp_port = str(s.getsockname()[1])
    env["AUTOUI_MCP_PORT"] = mcp_port
    proc = subprocess.Popen(
        [os.environ.get("AUTO_BIN",
                        r"D:\autostack\auto-man\target\debug\auto.exe"),
         "run", "-r", "vm", "--no-merge", "-B", "17825"],
        cwd=ROOT, env=env, stdout=logf, stderr=subprocess.STDOUT)
    proc.__logf = logf
    t0 = time.time()
    backend = False
    while time.time() - t0 < 300:
        if proc.poll() is not None:
            logf.close()
            raise RuntimeError(f"{log_name}: vm run exited rc={proc.returncode}")
        if not backend:
            try:
                http_json("http://127.0.0.1:17825/api/library/books", timeout=3)
                backend = True
                print(f"  [*] backend up in {time.time()-t0:.0f}s", flush=True)
            except Exception:
                time.sleep(2)
                continue
        try:
            text = open(log_path, encoding="utf-8", errors="replace").read()
            if f"AutoUI MCP: listening on http://127.0.0.1:{mcp_port}" in text:
                print(f"  [*] mcp up on {mcp_port} in {time.time()-t0:.0f}s", flush=True)
                return proc, mcp_port
        except Exception:
            pass
        time.sleep(2)
    logf.close()
    raise RuntimeError(f"{log_name}: vm backend={backend} mcp not ready in 300s")


def open_reading_page(client, failures, name):
    """VM 轨 UI 走查：书架卡 → 详情"继续阅读" → 阅读页挂载（派生/恢复生效）。"""
    import re as _re
    res = client.call("autoui_find", {"label": BOOK_TITLE})
    text = json.dumps(res, ensure_ascii=False)
    # 卡片点击宿主 = 带 events:{onclick} 的 row/col 节点
    m = _re.search(r"(?:row|col) (vnode_\d+) \{[^}]*events: \{onclick", text)
    target = m.group(1) if m else None
    if not target:
        failures.append(f"{name}: book card (onclick host) not found on shelf")
        return False
    client.call("autoui_action", {"element_id": target, "action": "press"})
    btn = ""
    for _ in range(20):
        time.sleep(1)
        r2 = client.call("autoui_find", {"kind": "button", "label": "继续阅读"})
        t2 = json.dumps(r2, ensure_ascii=False)
        bm = _re.search(r"button (vnode_\d+)", t2)
        if bm:
            btn = bm.group(1)
            break
    if not btn:
        failures.append(f"{name}: 继续阅读 button not found on detail page")
        return False
    client.call("autoui_action", {"element_id": btn, "action": "press"})
    time.sleep(4)  # 阅读页 Init（引擎装载序列）
    return True


def vm_leg(name, app_env, expect, failures, data_dir, log_name, log_grep=None):
    """VM 轨腿：MCP 状态哨兵 + 主区像素 + 工具宿主日志 grep。"""
    print(f"[*] leg {name} (vm)", flush=True)
    sweep_ports()
    if not (port_free(17824) and port_free(17825)):
        failures.append(f"{name}: ports busy (orphan instance)")
        return
    proc = None
    try:
        proc, mcp_port = boot_vm(app_env, data_dir, log_name)
        if not import_corpus():
            failures.append(f"{name}: corpus import failed")
            return
        client = Mcp(mcp_port)
        state = ""
        t0 = time.time()
        while time.time() - t0 < 240:
            try:
                s = client.state()
                if s and "dark_mode" in s:
                    state = s
                    break
            except Exception:
                pass
            time.sleep(1)
        if not state:
            failures.append(f"{name}: MCP state not ready in 240s")
            return
        time.sleep(4)  # settle: 策略发布 + 首帧应用
        state = client.state() or state
        # 书架面哨兵 + 像素（先于走查——阅读页铬面 token 值不同）
        for needle, why in expect.get("state", []):
            if needle in state:
                print(f"  [+] state ok: {why}", flush=True)
            else:
                failures.append(f"{name}: state sentinel missing: {needle} ({why})")
        if expect.get("pixel"):
            p = client.shot(f"059_{name}")
            time.sleep(1)
            if p and os.path.exists(p):
                shot = os.path.join(ART, f"{name}.png")
                with open(p, "rb") as s, open(shot, "wb") as d:
                    d.write(s.read())
                rgb = interior_pixel(shot)
                want = expect["pixel"]
                hexv = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
                tol = int(expect.get("pixel_tol", 0))
                print(f"  [*] interior pixel {hexv} (expect {want} ±{tol})", flush=True)
                if tol:
                    want_rgb = tuple(int(want[i:i + 2], 16) for i in (1, 3, 5))
                    if any(abs(a - b) > tol for a, b in zip(rgb, want_rgb)):
                        failures.append(f"{name}: pixel {hexv} != {want} ±{tol}")
                elif hexv != want:
                    failures.append(f"{name}: pixel {hexv} != {want}")
            else:
                failures.append(f"{name}: screenshot not saved")
        # 走查进阅读页后的哨兵（theme 派生/恢复在页 Init 时落位）
        if expect.get("open_book"):
            if open_reading_page(client, failures, name):
                state2 = client.state() or ""
                for needle, why in expect.get("state_post", []):
                    if needle in state2:
                        print(f"  [+] state ok: {why}", flush=True)
                    else:
                        failures.append(f"{name}: state sentinel missing: {needle} ({why})")
        with open(os.path.join(ART, f"state-{name}.txt"), "w", encoding="utf-8") as f:
            f.write(state)
        if log_grep:
            content = open(os.path.join(ART, log_name),
                           encoding="utf-8", errors="replace").read()
            for needle, why in log_grep:
                if needle in content:
                    print(f"  [+] log ok: {why}", flush=True)
                else:
                    failures.append(f"{name}: log sentinel missing: {needle} ({why})")
    except Exception as e:
        failures.append(f"{name}: {e}")
    finally:
        if proc is not None:
            stop(proc)


def port_free(port):
    for fam, addr in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
        with socket.socket(fam, socket.SOCK_STREAM) as sk:
            try:
                sk.bind((addr, port))
                return True
            except OSError:
                return False
    return False


def port_listeners(port):
    """PIDs listening on `port` (IPv4+IPv6) via netstat — session-owned sweep."""
    pids = set()
    try:
        out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                             timeout=20).stdout or ""
    except Exception:
        return pids
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[3] == "LISTENING" and parts[1].endswith(f":{port}"):
            try:
                pids.add(int(parts[4]))
            except ValueError:
                pass
    return pids


def sweep_ports():
    """Kill session-owned orphans on 17824/17825 (auto-reader path PIDs only)."""
    for port in (17824, 17825):
        for pid in port_listeners(port):
            try:
                cmd = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     f'(Get-CimInstance Win32_Process -Filter "ProcessId={pid}").CommandLine'],
                    capture_output=True, text=True, timeout=20).stdout or ""
            except Exception:
                cmd = ""
            if "auto-reader" in cmd or "plan-059" in cmd or "gen\\front\\vue" in cmd:
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                               capture_output=True, timeout=30)
                print(f"  [sweep] killed orphan {pid} on {port}")


def stop(proc):
    try:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True, timeout=30)
    except Exception:
        pass
    # 孤立子进程收割（vite/node/tool-host 脱离任务树——A/B 腿实证）：
    # 端口直至清空才继续，杜绝下一腿撞上读旧数据的幽灵实例。
    deadline = time.time() + 20
    while time.time() < deadline:
        if not port_listeners(17824) and not port_listeners(17825):
            break
        sweep_ports()
        time.sleep(2)
    try:
        logf = proc.__logf
        logf.flush()
        logf.close()
    except Exception:
        pass
    time.sleep(1)


def leg(name, app_env, expect, failures, data_dir, log_name, log_grep=None):
    print(f"[*] leg {name}", flush=True)
    sweep_ports()
    if not (port_free(17824) and port_free(17825)):
        failures.append(f"{name}: ports 17824/17825 busy (orphan instance)")
        return
    proc = None
    try:
        proc = boot(app_env, data_dir, log_name)
        if not import_corpus():
            failures.append(f"{name}: corpus import failed")
            return
        rc, out = run_spec(name, expect)
        tail = out.strip().splitlines()[-6:] if out.strip() else []
        print(f"  [*] playwright rc={rc}", flush=True)
        for line in tail:
            print("      " + line)
        if rc != 0:
            failures.append(f"{name}: spec failed rc={rc} (see spec-{name}.log)")
        if log_grep:
            log_path = os.path.join(ART, log_name)
            content = open(log_path, encoding="utf-8", errors="replace").read()
            for needle, why in log_grep:
                if needle in content:
                    print(f"  [+] log ok: {why}")
                else:
                    failures.append(f"{name}: log sentinel missing: {needle} ({why})")
    except Exception as e:
        failures.append(f"{name}: {e}")
    finally:
        if proc is not None:
            stop(proc)


def main() -> int:
    failures = []
    os.makedirs(ART, exist_ok=True)
    if not os.path.isfile(os.path.join(CORPUS, "product-alpha.epub")):
        print("[-] corpus missing (run gen_product_corpus.py first)")
        return 2
    auto_bin_env = {"AUTO_BIN": os.environ.get(
        "AUTO_BIN", r"D:\autostack\auto-man\target\debug\auto.exe")}

    # A: explicit override (AUTO_UI_THEME=dark)
    only = os.environ.get("T59_LEGS", "")
    run = lambda name: (not only) or name in only.split(",")

    if run("A"):
        leg("A", {"AUTO_UI_THEME": "dark"},
            {"T59_SHELL_RGB": AUTO_DARK_BG, "T59_READ_THEME": "dark",
             "T59_ENGINE_RGB": ENGINE_DARK_BG, "T59_BOOK": BOOK_TITLE,
             "T59_ART": os.path.join(ART, "legA")},
            failures, os.path.join(ART, "data-A"), "boot-A.log")

    # B: OS-follow default (env unset; light-OS machine -> light)
    if run("B"):
        leg("B", {},
            {"T59_SHELL_RGB": AUTO_LIGHT_BG, "T59_READ_THEME": "light",
             "T59_BOOK": BOOK_TITLE, "T59_ART": os.path.join(ART, "legB")},
            failures, os.path.join(ART, "data-B"), "boot-B.log")

    # F: standalone follow（VM 轨——跟随臂只武装 iced/VM 窗路径）:
    # AUTOOS_DESKTOP_CONFIG -> Solarized/dark, shell pixel #002b36 + dark_mode true
    cfg_f = os.path.join(ART, "cfg-follow", "config.at")
    write_solarized_config(cfg_f)
    if run("F"):
        vm_leg("F", {"AUTOOS_DESKTOP_CONFIG": cfg_f,
                     "AUTOOS_THEME_PACKAGE_DIR": r"D:\autostack\.wt\os-059\auto-ui\packages\themes"},
               {"state": [("dark_mode: true", "host policy derived mode dark")],
                "pixel": "#002b36", "open_book": True,
                "state_post": [("theme: \"dark\"", "reading default derived dark (no explicit choice)")]},
               failures, os.path.join(ART, "data-F"), "boot-F.log")

    # FB: bad digest candidate -> named rejection, keep legacy light (VM 轨)
    cfg_bad = os.path.join(ART, "cfg-bad", "config.at")
    write_solarized_config(cfg_bad, digest="0" * 64)
    if run("FB"):
        vm_leg("FB", {"AUTOOS_DESKTOP_CONFIG": cfg_bad,
                      "AUTOOS_THEME_PACKAGE_DIR": r"D:\autostack\.wt\os-059\auto-ui\packages\themes"},
               {"state": [("dark_mode: false", "bad candidate rejected, legacy light kept")],
                "pixel": "#ffffff"},
               failures, os.path.join(ART, "data-FB"), "boot-FB.log",
               log_grep=[("拒绝", "bad-digest candidate named rejection in tool host log")])

    # FR: reopen-to-latest（VM 轨）: config -> Auto/dark, fresh boot follows #09090b
    cfg_fr = os.path.join(ART, "cfg-reopen", "config.at")
    write_solarized_config(cfg_fr, family="Auto", mode="dark")
    if run("FR"):
        vm_leg("FR", {"AUTOOS_DESKTOP_CONFIG": cfg_fr,
                      "AUTOOS_THEME_PACKAGE_DIR": r"D:\autostack\.wt\os-059\auto-ui\packages\themes"},
               {"state": [("dark_mode: true", "reopen adopts latest policy")],
                "pixel": "#09090b"},
               failures, os.path.join(ART, "data-FR"), "boot-FR.log")

    # SL: Solarized x light（VM 轨）—— 两族×明暗矩阵补全（review R-1）
    cfg_sl = os.path.join(ART, "cfg-sl", "config.at")
    write_solarized_config(cfg_sl, mode="light")
    if run("SL"):
        vm_leg("SL", {"AUTOOS_DESKTOP_CONFIG": cfg_sl,
                      "AUTOOS_THEME_PACKAGE_DIR": r"D:\autostack\.wt\os-059\auto-ui\packages\themes"},
               {"state": [("dark_mode: false", "Solarized light derived mode")],
                "pixel": "#fdf6e2", "pixel_tol": 2},
               failures, os.path.join(ART, "data-SL"), "boot-SL.log")

    # S1: apply sepia via real UI picker (persists to reading-state), light boot（vue 轨）
    if run("S1"):
        leg("S1", {},
            {"T59_SHELL_RGB": AUTO_LIGHT_BG, "T59_READ_THEME": "sepia",
             "T59_ENGINE_RGB": ENGINE_SEPIA_BG, "T59_BOOK": BOOK_TITLE,
             "T59_APPLY_SEPIA": "1", "T59_ART": os.path.join(ART, "legS1")},
            failures, os.path.join(ART, "data-S"), "boot-S1.log")

    # S2: re-open under Solarized/dark follow（VM 轨, 复用 data-S 的 sepia 持久态）
    # -> 壳暗 #002b36 且阅读保持 sepia（显式 > follow）
    cfg_s = os.path.join(ART, "cfg-follow", "config.at")
    if run("S2"):
        vm_leg("S2", {"AUTOOS_DESKTOP_CONFIG": cfg_s,
                      "AUTOOS_THEME_PACKAGE_DIR": r"D:\autostack\.wt\os-059\auto-ui\packages\themes"},
               {"state": [("dark_mode: true", "host policy dark applied")],
                "pixel": "#002b36", "open_book": True,
                "state_post": [("theme: \"sepia\"", "explicit reading choice beats follow")]},
               failures, os.path.join(ART, "data-S"), "boot-S2.log")

    if failures:
        print("[-] FAILURES:", flush=True)
        for f in failures:
            print("   -", f)
        return 1
    print("[+] PLAN-059 reader theme counter-controls: all legs passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
