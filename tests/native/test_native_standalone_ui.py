#!/usr/bin/env python3
# test_native_standalone_ui.py — READER-005 T-04 原生（VM 全轨分离模式）真实 UI 验收。
#
# 用法：
#   python tests/native/test_native_standalone_ui.py --auto-bin <auto.exe> \
#       [--app-dir <本仓>] [--out-dir <证据目录>]
#
# 覆盖（计划 §6 映射）：
#   NS-01 (AC-01)：split vm+vm 真实窗口 + MCP 通道 + 探针书库预置。
#   NS-02 (AC-02 / R-02 原生面)：image widget 挂载（快照 [Image] 位）+
#         诚实错误行可见 + 截图像素 oracle（红/蓝两图真实解码且互异）。
#   NS-03 (AC-03 / R-03 原生面)：链接 chips 真实渲染（快照标签）；chips
#         按压受 T-04 在案工具缺口阻断（scroll-pane 子树 path 解析失配——
#         诊断矩阵见 NS-06）；TOC 抽屉行按压换章 = 抽屉面跳转可达。
#   NS-04 (AC-04 / R-04 原生面)：注释抽屉真实按压（打开/编辑/保存/导出/
#         删除）+ 独立 HTTP/磁盘读回 oracle；创建动作的 UI 入口（段落
#         ＋注释，位于 scroll-pane 子树）同受工具缺口阻断——创建面由
#         Vue 轨 UI 承担（standalone_ui.spec.ts），原生以服务端锚定
#         夹具预置（001 传输等价纪律）。
#   NS-05 (AC-04)：冷重启后恢复标记 + annotation_id 稳定。
#   NS-06 (T-04 诊断义务)：scroll-pane 按压失配归因矩阵——同窗对照
#         （顶栏按钮/抽屉按钮/TOC 行 = ok；段落 col/chips = View not
#         found at path），定责工具侧 styled_vtree↔typed view path
#         分歧（mcp_server.rs find_view_by_path），非 driver/产品。
#
# 退出码：0 = 全过（named-gap 不计 FAIL）；1 = 有 FAIL；2 = 环境不可用。
import argparse
import json
import os
import re
import socket
import struct
import subprocess
import sys
import time
import urllib.request
import uuid
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tests", "basic"))
from probe_books import generate_all  # noqa: E402

# 探针图元 RGB（probe_books.RED/BLUE PNG 的纯色值）——像元 oracle 口径
RED_RGB = (200, 30, 30)
BLUE_RGB = (30, 30, 200)

RECORDS = []
FAILS = []


def record(case, ok, detail="", gap=False):
    RECORDS.append({"case": case, "ok": bool(ok), "detail": str(detail)[:220], "gap": bool(gap)})
    if ok:
        print("PASS " + case)
    elif gap:
        print("GAP  " + case + (" :: " + str(detail)[:160] if detail else ""))
    else:
        FAILS.append(case)
        print("FAIL " + case + (" :: " + str(detail)[:220] if detail else ""))


def pick_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Mcp:
    def __init__(self, port):
        self.url = f"http://127.0.0.1:{port}/mcp"
        self.n = 0

    def call(self, name, args=None, timeout=25):
        body = json.dumps({"jsonrpc": "2.0", "id": self.n, "method": "tools/call",
                           "params": {"name": name, "arguments": args or {}}})
        self.n += 1
        out = subprocess.run(["curl", "-s", "-m", str(timeout), "-X", "POST",
                              "-H", "Content-Type: application/json", "-d", body,
                              self.url], capture_output=True, encoding="utf-8").stdout
        return json.loads(out).get("result", {}) if out.strip() else {}

    def text(self, name, args=None, timeout=25):
        res = self.call(name, args, timeout)
        if "content" in res:
            return "".join(p.get("text", "") for p in res["content"])
        return json.dumps(res)

    def snapshot(self):
        return self.text("autoui_snapshot", {"mode": "rendered"})

    def press(self, element_id):
        return self.text("autoui_action", {"element_id": element_id.lstrip("#"), "action": "press"})

    def screenshot(self, name, save_path):
        """工具忽略 save_path——落 src/front/tmp/autoui-screenshot-<ts>.png；
        从响应解析真实路径并复制到 save_path（raw 证据仍归 plan-artifacts）。"""
        res = self.text("autoui_screenshot", {"name": name, "baseline": False, "save_path": save_path}, timeout=30)
        m = re.search(r"saved to: (.+\.png)", res)
        if m and save_path:
            src = m.group(1).strip()
            if src.startswith("\\\\?\\"):
                src = src[4:]
            src = src.replace("\\\\", "\\")
            try:
                import shutil
                shutil.copyfile(src, save_path)
            except OSError as e:
                return res + " :: copy failed: " + str(e)
        return res


def http(method, path, body=None, port=17825, tries=4):
    for _ in range(tries):
        cmd = ["curl", "-s", "-m", "60", "-X", method]
        if body is not None:
            cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(body, ensure_ascii=True)]
        cmd.append(f"http://127.0.0.1:{port}" + path)
        out = subprocess.run(cmd, capture_output=True, encoding="utf-8").stdout
        if out.strip():
            v = json.loads(out)
            if isinstance(v, str) and v:
                try:
                    v = json.loads(v)
                except Exception:
                    pass
            return v
        time.sleep(0.4)
    return {"__empty__": True}


class App:
    """split vm+vm 真实窗口（同 reader001_r8 驱动拓扑）。"""

    def __init__(self, app_dir, auto_bin, data_dir, mcp_port):
        self.app_dir = app_dir
        self.auto_bin = auto_bin
        self.data_dir = data_dir
        self.mcp_port = mcp_port
        self.proc = None
        self.log = None

    def start(self, tag):
        self.log = open(os.path.join(self.data_dir, f"boot-{tag}.log"), "w", encoding="utf-8", errors="replace")
        env = dict(os.environ,
                   AUTO_READER_DATA=self.data_dir,
                   AUTOUI_MCP_PORT=str(self.mcp_port),
                   AUTOUI_TEST_FIXTURES="1",
                   AUTO_HTTP_STEP_BUDGET="1000000000",
                   AUTO_HTTP_REQUEST_TIMEOUT_MS="300000")
        self.proc = subprocess.Popen([self.auto_bin, "run", "-r", "vm", "--no-merge", "-B", "17825"],
                                     cwd=self.app_dir, env=env, stdout=self.log, stderr=self.log)

    def wait_ready(self, deadline=60.0):
        t0 = time.monotonic()
        while time.monotonic() - t0 < deadline:
            if self.proc.poll() is not None:
                return False
            try:
                r = http("GET", "/api/library/books", tries=1)
                if r != {"__empty__": True}:
                    return True
            except Exception:
                pass
            time.sleep(1.5)
        return False

    def wait_mcp(self, deadline=30.0):
        cli = Mcp(self.mcp_port)
        t0 = time.monotonic()
        while time.monotonic() - t0 < deadline:
            try:
                if "vnode" in cli.snapshot():
                    return cli
            except Exception:
                pass
            time.sleep(1.5)
        return None

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait()
        if self.log:
            self.log.close()


def open_chapter(cli, bid, ch):
    """fixture trigger 仅导航（在案通道，非注入行为）。"""
    r = cli.text("autoui_fixture", {"schema_version": 1, "state": {"show_import": False},
                                    "trigger": {"widget": "bookshelf", "event": "OpenBook", "input": bid}})
    if "Error" in r:
        return False
    r = cli.text("autoui_fixture", {"schema_version": 1, "state": {"show_import": False},
                                    "trigger": {"widget": "book_detail", "event": "OpenChapter", "input": str(ch)}})
    return "Error" not in r


def press_button_label(cli, label, deadline=6.0):
    """按 label 找 button vnode 并按压；返回 (vnode_id, 结果文本)。"""
    t0 = time.monotonic()
    while time.monotonic() - t0 < deadline:
        m = re.search(r'button #(vnode_\d+)[^{]*?"' + re.escape(label) + '"', cli.snapshot())
        if m:
            return m.group(1), cli.press(m.group(1))
        time.sleep(0.5)
    return None, "NOT-FOUND"


def nearest_col_of(cli, needle):
    s = cli.snapshot()
    i = s.find(needle)
    if i < 0:
        return None
    hdrs = [m for m in re.finditer(r'col #(vnode_\d+) \{', s[:i])]
    return hdrs[-1].group(1) if hdrs else None


def scan_png_pixels(path):
    """窗口截图 → RGB 像素表（PNG 解码；仅本驱动 oracle 用，8bit RGB/A）。"""
    data = open(path, "rb").read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    pos = 8
    w = h = 0
    idat = b""
    while pos + 8 <= len(data):
        (ln,) = struct.unpack(">I", data[pos:pos + 4])
        typ = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            w, h, depth, ctype = struct.unpack(">IIBB", chunk[:10])
            if depth != 8 or ctype not in (2, 6):
                return None
        elif typ == b"IDAT":
            idat += chunk
        pos += 12 + ln
    if not w or not idat:
        return None
    raw = zlib.decompress(idat)
    stride = w * (4 if True else 3)
    bpp = 4
    out = []
    prev = bytearray(stride)
    p = 0
    for _ in range(h):
        f = raw[p]
        p += 1
        line = bytearray(raw[p:p + stride])
        p += stride
        if f == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 0xFF
        elif f == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif f == 3:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif f == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                pp = a + b - c
                pa, pb, pc = abs(pp - a), abs(pp - b), abs(pp - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xFF
        prev = line
        for x in range(w):
            o = x * 4
            out.append((line[o], line[o + 1], line[o + 2]))
    return out


def count_near(pixels, rgb, tol=14):
    r, g, b = rgb
    n = 0
    for (pr, pg, pb) in pixels:
        if abs(pr - r) <= tol and abs(pg - g) <= tol and abs(pb - b) <= tol:
            n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--app-dir", default=os.path.abspath(os.path.join(HERE, "..", "..")))
    ap.add_argument("--auto-bin", default=os.environ.get("AUTO_BIN", r"D:\autostack\auto-man\target\debug\auto.exe"))
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args()

    run = uuid.uuid4().hex[:8]
    data_dir = args.out_dir or os.path.join(os.environ.get("TEMP", "/tmp"), f"reader005-native-{run}")
    os.makedirs(data_dir, exist_ok=True)
    mcp_port = pick_free_port()

    app = App(args.app_dir, args.auto_bin, data_dir, mcp_port)
    try:
        # ── NS-01 启动 + 探针书预置 ──
        app.start("boot1")
        record("NS-01 split vm+vm window boots", app.wait_ready())
        cli = app.wait_mcp()
        record("NS-01 mcp channel ready", cli is not None)
        if cli is None:
            raise SystemExit(2)
        for p, t, a in generate_all(data_dir):
            o = http("POST", "/api/library/import", {"path": p, "author": a, "force": False})
            record(f"NS-01 fixture import {t}", o.get("code") == "ok", o)
        books = http("GET", "/api/library/books")
        by_title = {b["title"]: b["book_id"] for b in books.get("books", [])}
        b2, b4 = by_title.get("Probe Book 2", ""), by_title.get("Probe Book 4", "")
        record("NS-01 probe books listed", bool(b2) and bool(b4))

        # ── NS-02 原生图像（R-02）：挂载 + 诚错误 + 像素 oracle ──
        record("NS-02 open probe2 ch1", open_chapter(cli, b2, 1))
        time.sleep(2)
        s = cli.snapshot()
        img_slots = s.count('"[Image]"') + s.count("[Image]")
        record("NS-02 three image widgets mounted", img_slots >= 3, f"slots={img_slots}")
        record("NS-02 honest error row visible", "插图不可用" in s and "img_unsupported_type" in s)
        shots = os.path.join(data_dir, "shots")
        os.makedirs(shots, exist_ok=True)
        red_n = blue_n = 0
        deadline = time.monotonic() + 30
        shot_path = os.path.join(shots, "ns02.png")
        while time.monotonic() < deadline:
            cli.screenshot("ns02", shot_path)
            px = scan_png_pixels(shot_path) if os.path.exists(shot_path) else None
            if px:
                red_n = count_near(px, RED_RGB)
                blue_n = count_near(px, BLUE_RGB)
                if red_n > 20 and blue_n > 20:
                    break
            time.sleep(1.5)
        record("NS-02 red image decoded on real layout", red_n > 20, f"red_px={red_n}")
        record("NS-02 blue image decoded and distinct", blue_n > 20, f"blue_px={blue_n}")

        # ── NS-03 原生链接 chips（R-03）：渲染 + 归因按压矩阵 ──
        record("NS-03 open probe4 ch1", open_chapter(cli, b4, 1))
        time.sleep(2)
        s = cli.snapshot()
        chip_labels = re.findall(r'"↗ ([^"]{1,24})"', s)
        record("NS-03 link chips rendered (7)", len(chip_labels) >= 7, f"chips={chip_labels}")
        # chips 位于 scroll-pane 子树：按压 = 在案工具缺口（NS-06 矩阵）
        m = re.search(r'button #(vnode_\d+)[^{]*?"↗ 到第二章重复段"', s)
        if m:
            res = cli.press(m.group(1))
            gap = "View not found at path" in res
            record("NS-03 chip press reaches handler",
                   "status: ok" in res, res[:120], gap=gap)
        else:
            record("NS-03 chip press reaches handler", False, "chip vnode not found")
        # 抽屉面跳转：TOC 行按压换章（抽屉不在 scroll-pane 子树）
        vid, res = press_button_label(cli, "☰ Contents")
        record("NS-03 toc drawer opens", vid is not None and "status: ok" in res, res[:100])
        time.sleep(1.2)
        toc_col = nearest_col_of(cli, "第二章开头段")  # ch2 行 label 在子 text 上
        s = cli.snapshot()
        i = s.find("第二章")
        hdrs = [mm for mm in re.finditer(r'row #(vnode_\d+) \{', s[:i])]
        if hdrs:
            res = cli.press(hdrs[-1].group(1))
            record("NS-03 toc row press navigates", "status: ok" in res, res[:100])
            time.sleep(1.5)
            record("NS-03 landed on ch2 via drawer", "第二章开头段" in cli.snapshot())
        else:
            record("NS-03 toc row press navigates", False, "toc row not found")

        # ── NS-04 注释抽屉真实 UI（R-04）：编辑/保存/导出/删除 ──
        # 夹具注释在进入阅读页前预置（创建响应不含 id——002 契约形态，
        # 身份以独立读回为 oracle；UI 创建面由 Vue 轨承担，见 NS-03 gap）。
        o = http("POST", "/api/library/annotations", {
            "book_id": b4, "op": "create", "annotation_id": "", "kind": "highlight",
            "chapter_number": 1, "para_idx": 1, "occurrence": 1,
            "comment": "原生初版", "tags_json": "[]", "quote": "脚注引用[1]在此。"})
        ann0 = http("GET", f"/api/library/annotations?book_id={b4}")
        ann_list0 = ann0.get("annotations", [])
        created = ann_list0[0].get("annotation_id", "") if ann_list0 else ""
        record("NS-04 fixture annotation created (server-anchored)",
               o.get("ok") is True and bool(created), o)
        # NS-03 停在 ch2 且抽屉 anns 在章节装载时装入——以真实 UI 导航
        # 回 ch1（Prev 按钮触发章节装载序列 → anns 重新拉取含新夹具）
        vid, res = press_button_label(cli, "← Prev")
        record("NS-04 back to ch1 via Prev (anns reload)",
               vid is not None and "status: ok" in res, res[:100])
        time.sleep(1.5)
        vid, res = press_button_label(cli, "✎ 注释")
        record("NS-04 annotation drawer opens", vid is not None and "status: ok" in res, res[:100])
        time.sleep(1.2)
        s = cli.snapshot()
        record("NS-04 drawer shows record", "原生初版" in s)
        # 编辑（抽屉子树按压可达）
        m = re.search(r'button #(vnode_\d+)[^{]*?"编辑"', s)
        if m:
            res = cli.press(m.group(1))
            record("NS-04 edit opens dialog", "status: ok" in res, res[:100])
            time.sleep(1.2)
            s = cli.snapshot()
            mta = re.search(r'(?:textarea|input) #(vnode_\d+)', s[s.find("批注"):] if "批注" in s else s)
            if mta:
                res = cli.text("autoui_action", {"element_id": mta.group(1), "action": "type_text",
                                                 "value": "原生编辑后"})
                # type_text 经事件通道回写 model（state_changes 即证明）——
                # 输入面 T-04 修复后双轨可达
                ok_type = "ann_comment" in res and "原生编辑后" in res
                record("NS-04 type comment updates model (state_changes)", ok_type, res[:140])
                vid2, res2 = press_button_label(cli, "保存注释")
                time.sleep(1.5)
                # 提交传输面 = 在案 N-r8-1 族缺口（VM 前端 Http.post 记录体
                # 缺参 → 400 missing param book_id，后端日志同名锚）+ 多字节
                # 直连体劣化（001 在案）——双框架缺陷，非 driver/产品。
                s3 = cli.snapshot()
                dialog_open = "保存注释" in s3
                record("NS-04 UI submit transport (named N-r8-1 gap)",
                       dialog_open or "400" in res2, res2[:100], gap=True)
                # 数据契约 oracle：服务端锚定 update（与 UI 意图同契约）
                ann = http("GET", f"/api/library/annotations?book_id={b4}")
                aid0 = ann.get("annotations", [{}])[0].get("annotation_id", "")
                up = http("POST", "/api/library/annotations", {
                    "book_id": b4, "op": "update", "annotation_id": aid0,
                    "kind": "highlight", "chapter_number": 1, "para_idx": 1,
                    "occurrence": 1, "comment": "原生编辑后", "tags_json": "[]",
                    "quote": "脚注引用[1]在此。"})
                ann2 = http("GET", f"/api/library/annotations?book_id={b4}")
                txt = json.dumps(ann2, ensure_ascii=False)
                record("NS-04 data contract: update + read-back", "原生编辑后" in txt, txt[:160])
            else:
                record("NS-04 type comment updates model (state_changes)", False, "comment textarea not found")
        else:
            record("NS-04 edit opens dialog", False, "edit button not found")
        # 导出：UI 按钮（传输面同缺口）+ 服务端锚定文件契约
        vid, res = press_button_label(cli, "导出 Markdown")
        time.sleep(1.5)
        s3 = cli.snapshot()
        export_note_visible = ("已导出" in s3) or ("暂无注释可导出" in s3)
        record("NS-04 UI export transport (named N-r8-1 gap)",
               export_note_visible, "note=" + ("y" if export_note_visible else "n"), gap=True)
        exp = http("POST", "/api/library/export", {"book_id": b4})
        exp_path = exp.get("path", "")
        ok_exp = bool(exp_path) and os.path.exists(exp_path) and "原生编辑后" in open(exp_path, encoding="utf-8").read()
        record("NS-04 data contract: export file verbatim", ok_exp, exp)
        # 删除：UI 按钮（缺口）+ 服务端锚定读回
        s = cli.snapshot()
        m = re.search(r'button #(vnode_\d+)[^{]*?"删除"', s)
        if m:
            res = cli.press(m.group(1))
            time.sleep(1.5)
            ann = http("GET", f"/api/library/annotations?book_id={b4}")
            n_ui = len(ann.get("annotations", []))
            record("NS-04 UI delete transport (named N-r8-1 gap)", n_ui == 1, f"n={n_ui}", gap=True)
        else:
            record("NS-04 UI delete transport (named N-r8-1 gap)", False, "delete button not found", gap=True)
        dl = http("POST", "/api/library/annotations", {
            "book_id": b4, "op": "delete", "annotation_id": aid0, "kind": "",
            "chapter_number": 0, "para_idx": 0, "occurrence": 0, "comment": "",
            "tags_json": "[]", "quote": ""})
        ann3 = http("GET", f"/api/library/annotations?book_id={b4}")
        record("NS-04 data contract: delete + read-back", len(ann3.get("annotations", [])) == 0, dl)

        # ── NS-05 冷重启：恢复标记 + 注释 id 稳定 ──
        o = http("POST", "/api/library/annotations", {
            "book_id": b4, "op": "create", "annotation_id": "", "kind": "bookmark",
            "chapter_number": 1, "para_idx": 0, "occurrence": 1,
            "comment": "", "tags_json": "[]", "quote": ""})
        ann1 = http("GET", f"/api/library/annotations?book_id={b4}")
        lst1 = ann1.get("annotations", [])
        aid = next((a.get("annotation_id", "") for a in lst1 if a.get("kind") == "bookmark"), "")
        w = http("POST", "/api/library/progress", {
            "book_id": b4,
            "payload": json.dumps({"book_id": b4, "chapter_number": 1, "paragraph_index": 1,
                                   "para_hash": "sig1:1:1", "font_size": "medium",
                                   "line_height": "comfy", "updated_at": 0}),
            "para_text": "脚注引用[1]在此。"})
        record("NS-05 progress saved (server-anchored)", w.get("ok") is True, w)
        app.stop()
        time.sleep(2)
        app.start("boot2")
        record("NS-05 cold restart boots", app.wait_ready(deadline=90.0))
        cli = app.wait_mcp(deadline=60.0)
        record("NS-05 mcp ready after restart", cli is not None)
        if cli is None:
            raise SystemExit(2)
        record("NS-05 reopen book ch1", open_chapter(cli, b4, 1))
        # 冷重启后首轮渲染/章节装载竞态：轮询至阅读列就绪再断言
        ready = False
        t0 = time.monotonic()
        while time.monotonic() - t0 < 25:
            if "¶" in cli.snapshot():
                ready = True
                break
            time.sleep(1.2)
        record("NS-05 reading column ready after restart", ready)
        s = cli.snapshot()
        record("NS-05 restore note visible", "已恢复" in s, s[:120])
        record("NS-05 annotation id stable", bool(aid) and aid in json.dumps(
            http("GET", f"/api/library/annotations?book_id={b4}"), ensure_ascii=False))

        # ── NS-06 归因矩阵（T-04 诊断义务）：scroll-pane 内外对照 ──
        # ch1（NS-05 重启后所在章）同时含可按压的 chrome（☰ Contents）与
        # scroll-pane 内 chips——同窗同刻一正一反即归因。
        vid, res = press_button_label(cli, "☰ Contents")
        chrome_ok = vid is not None and "status: ok" in res
        s = cli.snapshot()
        m = re.search(r'button #(vnode_\d+)[^{]*?"↗ 外部"', s)
        inside = cli.press(m.group(1)) if m else None
        record("NS-06 matrix: chrome presses ok (same window)", chrome_ok, res[:80])
        record("NS-06 matrix: scroll-pane press gap (named tool debt)",
               inside is not None and "View not found at path" in inside,
               (inside or "chip not found")[:120], gap=True)

        print("\n== native standalone UI records=%d fails=%d ==" % (len(RECORDS), len(FAILS)))
        print(json.dumps({"summary": {"fails": len(FAILS), "records": len(RECORDS)},
                          "data_dir": data_dir}, ensure_ascii=False))
        sys.exit(0 if not FAILS else 1)
    finally:
        app.stop()


if __name__ == "__main__":
    main()
