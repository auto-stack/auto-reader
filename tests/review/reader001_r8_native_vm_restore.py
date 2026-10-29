#!/usr/bin/env python3
"""READER-001 r8 T-26/T-15：原生 VM 轨恢复行为验收驱动（PLAN-781 验收通道）。

场景（V-21 原生门 / AC-02 原生 VM 目标可见）：
  1. `auto run -r vm --no-merge -B 17825` 原生 iced 窗口 + VM HTTP 后端，
     隔离 AUTO_READER_DATA（reader001-review-nativewm-*）+ 预算 profile。
  2. 导入与进度保存走 library HTTP（与 UI 点段/导入传输等价——Vue 轨
     real-book 套件同口径）。如实登记：VM 轨导入对话框臂的 store→Http.post
     裸记录体存在预存序列化缺陷（400 missing param path，Vue 轨正常；
     本 diff 未触该面）——登记 N-r8-1 跨仓候选，不属于本计划门。
  3. 冷重启（杀进程树→同目录重启）。
  4. 导航：fixture trigger OpenBook（书卡为 col onclick，MCP 无 col 点击
     原语；AUTOUI_TEST_FIXTURES 测试通道，仅用于导航，不注入恢复行为）
     → 「继续阅读」真按钮。
  5. oracle：autoui_visibility（真实布局帧）目标段 ¶50 正面积可见 +
     autoui_scroll_state pane offset 深位置 + ¶100 反差（未滚到尾部）。

诚实边界：恢复滚动/标记/提示全部为产品行为；fixture 仅导航。混排夹具
（4000 字长段 + 100 短段）即 F-12 反例构型——占比估算定位在该构型下失准
（r4/r5 实测 pane 外），锚点机制按真实布局定位。

用法：python tests/review/reader001_r8_native_vm_restore.py [--reader-dir DIR] [--auto-bin EXE]
前置：17825/17999 空闲； chromium 无关；独立数据目录由驱动创建。
"""
import argparse
import json
import os
import re
import socket
import subprocess
import sys
import time
import uuid

FAILS = []
RECORDS = []


def record(case, ok, detail=""):
    RECORDS.append({"case": case, "ok": bool(ok), "detail": str(detail)[:220]})
    if ok:
        print("PASS " + case)
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

    def jtext(self, name, args=None, timeout=25):
        return json.loads(self.text(name, args, timeout))

    def snapshot(self):
        return self.text("autoui_snapshot", {"mode": "rendered"})

    def press_button(self, label_re, deadline=8.0):
        t0 = time.monotonic()
        while time.monotonic() - t0 < deadline:
            m = re.search(r'button #(vnode_\d+)[^{]*?"' + label_re + '"', self.snapshot())
            if m:
                res = self.text("autoui_action", {"element_id": m.group(1), "action": "press"})
                if "status: ok" in res:
                    return True
            time.sleep(0.6)
        return False

    def col_of(self, needle):
        s = self.snapshot()
        i = s.find(needle)
        if i < 0:
            return None
        hdrs = [m for m in re.finditer(r"col #(vnode_\d+) \{", s[:i])]
        return hdrs[-1].group(1) if hdrs else None


def http(method, path, body=None, tries=4):
    for _ in range(tries):
        cmd = ["curl", "-s", "-m", "60", "-X", method]
        if body is not None:
            cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(body, ensure_ascii=True)]
        cmd.append("http://127.0.0.1:17825" + path)
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
    def __init__(self, reader_dir, auto_bin, data_dir, mcp_port):
        self.reader_dir = reader_dir
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
                                     cwd=self.reader_dir, env=env, stdout=self.log, stderr=self.log)

    def wait_ready(self, deadline=45.0):
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
                if "AURA Snapshot" in cli.snapshot():
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reader-dir", default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    ap.add_argument("--auto-bin", default=os.environ.get("AUTO_BIN", r"D:\autostack\auto-man\target\debug\auto.exe"))
    args = ap.parse_args()

    run = uuid.uuid4().hex[:8]
    data_dir = os.path.join(os.environ["TEMP"], f"reader001-review-nativewm-{run}")
    os.makedirs(data_dir, exist_ok=True)
    mcp_port = pick_free_port()

    # 混排夹具（F-12 反例构型）
    fx = os.path.join(data_dir, f"mixed-{run}.txt")
    with open(fx, "w", encoding="utf-8", newline="\n") as f:
        lines = [f"第一章 混排 {run}", "长" * 4000] + [f"短段{i} {run}" for i in range(1, 101)]
        f.write("\n".join(lines) + "\n")

    app = App(args.reader_dir, args.auto_bin, data_dir, mcp_port)
    try:
        # ── 阶段 1：首启动 + 导入/进度（library HTTP，传输等价） ──
        app.start("boot1")
        record("app boots (split vm+http)", app.wait_ready())
        cli = app.wait_mcp()
        record("mcp channel ready", cli is not None)
        if cli is None:
            raise SystemExit(1)

        o = http("POST", "/api/library/import", {"path": fx, "author": "nativewm", "force": False})
        record("import ok via library API", o.get("code") == "ok", o)
        bid = o.get("book_id", "")
        books = http("GET", "/api/library/books")
        mine = [b for b in books.get("books", []) if b.get("book_id") == bid]
        record("library lists the book", len(mine) == 1, books)
        ch = http("GET", f"/api/library/chapter?book_id={bid}&number=1")
        ml = ch.get("body", "").split("\n")
        record("chapter body line 50 is a short paragraph", ml[50].startswith("短段"), ml[50][:20])
        w = http("POST", "/api/library/progress", {
            "book_id": bid,
            "payload": json.dumps({"book_id": bid, "chapter_number": 1, "paragraph_index": 50,
                                   "para_hash": "sig1:1:1", "font_size": "medium",
                                   "line_height": "comfy", "updated_at": 0}),
            "para_text": ml[50].strip()})
        record("progress saved (pi=50)", w.get("ok") is True, w)

        # ── 阶段 3：冷重启 ──
        app.stop()
        time.sleep(2)
        app.start("boot2")
        record("cold restart boots", app.wait_ready())
        cli = app.wait_mcp()
        record("mcp ready after restart", cli is not None)
        if cli is None:
            raise SystemExit(1)

        # ── 阶段 4：导航（fixture trigger 仅导航）→ 阅读页 ──
        r = cli.text("autoui_fixture", {"schema_version": 1, "state": {"show_import": False},
                                        "trigger": {"widget": "bookshelf", "event": "OpenBook", "input": bid}})
        record("OpenBook trigger accepted", "Error" not in r, r[:120])
        detail = False
        for _ in range(10):
            time.sleep(1.5)
            if "继续阅读" in cli.snapshot():
                detail = True
                break
        record("detail page mounted", detail)
        # OpenChapter 亦走 fixture（autoui_action 按压通道的 handler 内
        # router.push 为 no-op——登记 N-r8-3 通道缺陷；fixture 派发的
        # push 正常，rt 实测路由推进）
        r = cli.text("autoui_fixture", {"schema_version": 1, "state": {"show_import": False},
                                        "trigger": {"widget": "book_detail", "event": "OpenChapter", "input": "1"}})
        record("OpenChapter trigger accepted", "Error" not in r, r[:120])

        # ── 阶段 5：恢复 oracle ──
        restored = False
        pi50 = None
        for _ in range(14):
            time.sleep(1.2)
            s = cli.snapshot()
            if "已恢复" in s:
                restored = True
            i = s.find("¶50")
            if i >= 0:
                hdrs = [mm for mm in re.finditer(r"col #(vnode_\d+) \{", s[:i])]
                if hdrs:
                    pi50 = hdrs[-1].group(1)
            if restored and pi50:
                break
        record("restore note shown (已恢复)", restored)
        record("target ¶50 rendered", pi50 is not None)

        vis_ok = False
        vis_detail = {}
        if pi50:
            for _ in range(10):
                try:
                    v = cli.jtext("autoui_visibility", {"element_id": pi50})
                except Exception as e:
                    vis_detail = {"err": str(e)}
                    time.sleep(1.2)
                    continue
                vis_detail = v
                tr = v.get("target_rect")
                if v.get("visible") and tr and tr[3] > 0:
                    vis_ok = True
                    break
                time.sleep(1.2)
        record("¶50 visible on real layout frame (positive area)", vis_ok, vis_detail)

        st = cli.jtext("autoui_scroll_state", {"pane": "reading-pane"})
        panes = [p for p in st.get("panes", []) if p.get("key") == "scroll_ctl_reading-pane"]
        offset_y = panes[0]["offset"][1] if panes else None
        record("reading-pane scrolled deep (offset>2000)", offset_y is not None and offset_y > 2000,
               {"offset_y": offset_y, "panes": st.get("panes", [])[:2]})

        # 反差：恢复定位到 ¶50（中部），尾部 ¶100 不得可见
        i100 = cli.snapshot().find("¶100")
        if i100 >= 0:
            hdrs = [mm for mm in re.finditer(r"col #(vnode_\d+) \{", cli.snapshot()[:i100])]
            if hdrs:
                try:
                    v100 = cli.jtext("autoui_visibility", {"element_id": hdrs[-1].group(1)})
                    record("contrast: ¶100 (tail) not visible", not v100.get("visible"), v100.get("target_rect"))
                except Exception as e:
                    record("contrast: ¶100 (tail) not visible", False, str(e))
            else:
                record("contrast: ¶100 (tail) not visible", True, "node gone (virtualized/absent)")
        else:
            record("contrast: ¶100 (tail) not visible", True, "¶100 not in tree")

        print(json.dumps({"summary": {"fails": len(FAILS), "records": len(RECORDS)},
                          "data_dir": data_dir}, ensure_ascii=False, indent=1))
    finally:
        app.stop()
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
