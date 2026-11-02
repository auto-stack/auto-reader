#!/usr/bin/env python3
# driver_vue.py — PLAN-026 Vue profile 表面驱动（V-01/V-02/V-03 + HTTP 负控）。
# 真实表面：reader 真实导入契约建立身份 → 探针消费 app（AutoVM .at 后端 +
# 生成 Vue 页 remote-frame 接缝）→ Playwright 真实 Chromium 注入引擎胶水
# （不代选：真实 mouse down/move/up 拖选）→ .at handler → sidecar 独立读回
# → 冷重启同 CFI 恢复原句。
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(HERE, "app")
READER_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ENGINE_REVISION = "foliate-js@3d794195"

INJECT = """
    import('/api/probe/asset/engine-adapter.js').then(m =>
      m.mountProbe({
        host: document.querySelector('[data-remote-frame]'),
        documentUrl: '/api/probe/document/%s/file',
        locatorUrl: '/api/probe/locator',
        sessionId: '%s',
        bookId: '%s',
        sourceHash: '%s',
        onStatus: (msg) => { document.title = 'probe:' + msg; }
      }));
"""


def http(method, url, body=None, timeout=60):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        v = json.loads(r.read().decode("utf-8"))
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return {"_raw": v}
    return v


class Instance:
    def __init__(self, cwd, log_path, env):
        self.log = open(log_path, "w", encoding="utf-8", errors="replace")
        e = dict(os.environ)
        e.update(env)
        e["AUTO_HTTP_STEP_BUDGET"] = "1000000000"
        e["AUTO_HTTP_REQUEST_TIMEOUT_MS"] = "300000"
        auto = os.environ.get("PROBE_AUTO_BIN", "auto")
        self.proc = subprocess.Popen([auto, "run", "--server=vm"], cwd=cwd,
                                     env=e, stdout=self.log, stderr=self.log)

    def wait(self, url, deadline=90):
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
            self.proc.kill()
            self.proc.wait()
        self.log.close()


def mount_and_wait(page, ident, sid):
    """注入引擎胶水并等待挂载；返回 (ready, load_ms_or_None)。"""
    page.goto("http://localhost:17826/#/", wait_until="networkidle")
    seam = page.locator("[data-remote-frame]")
    seam.wait_for(state="visible", timeout=15000)
    page.add_script_tag(content=INJECT % (ident["book_id"], sid,
                                           ident["book_id"], ident["source_hash"]),
                        type="module")
    t0 = time.monotonic()
    while time.monotonic() - t0 < 20:
        if page.evaluate(
                "() => window.__probe ? window.__probe.engine : null") == ENGINE_REVISION:
            return True, page.evaluate("() => window.__probe.loadMs")
        time.sleep(0.5)
    return False, None


def _iframe_page_x(page):
    """foliate 分页可视位移：paginator shadow 内 iframe 元素的页面 x。"""
    return page.evaluate(
        "() => { const v = document.querySelector('foliate-view');"
        " const p = v && v.shadowRoot && v.shadowRoot.querySelector('foliate-paginator');"
        " const f = p && p.shadowRoot && p.shadowRoot.querySelector('iframe');"
        " return f ? Math.round(f.getBoundingClientRect().x) : null; }")


def _vue_page_to_visible(page, para, host_bb, max_turns=48):
    """真实翻页（renderer.next()，许可口径：引擎翻页通道，非代选）直至
    目标段与 remote-frame 可视区相交。t09-vuediag9 实测：next() 以 iframe
    元素整页位移推进（每步 625px）；巨列形态下第2处出现在第 ~20 列——
    旧 12 轮上限不可达，且永不相交时旧代码以负宽插值算出视口外坐标（0
    locator POST 根因）。返回 (bb, turns, note)；bb=None = 预算内不可达/
    next 失去位移（具名，不吞）。"""
    def _box():
        try:
            return para.bounding_box()
        except Exception:
            return None

    bb = _box()
    turns = 0
    while turns < max_turns:
        if bb is None:
            return None, turns, "target box unresolved"
        ix0 = max(bb["x"], host_bb["x"])
        ix1 = min(bb["x"] + bb["width"], host_bb["x"] + host_bb["width"])
        iy0 = max(bb["y"], host_bb["y"])
        iy1 = min(bb["y"] + bb["height"], host_bb["y"] + host_bb["height"])
        if ix1 - ix0 > 60 and iy1 - iy0 > 24:
            return bb, turns, "visible"
        fx = _iframe_page_x(page)
        page.evaluate("() => window.__probe.view.renderer.next()")
        page.wait_for_timeout(650)
        fx2 = _iframe_page_x(page)
        if fx2 == fx:
            # 宽限复核：200% 重排等大内容过渡下动画未落位会误判卡死
            page.wait_for_timeout(1100)
            fx2 = _iframe_page_x(page)
        if fx is None or fx2 is None or fx2 == fx:
            return None, turns, f"next() stopped moving visible column (x {fx}->{fx2})"
        turns += 1
        bb = _box()
    return None, turns, f"target never intersects visible seam within {max_turns} turns"


def _vue_drag_and_verify(page, results, oracle_scan, tag, repeat_a,
                         host_sel="[data-remote-frame]"):
    """在当前布局下重新定位 repeat_a 第2处出现 → 真实 Playwright 鼠标拖选
    → 事件/预言机核验。返回 (ok, quote, occ, cfi, respj)。"""
    tframe = None
    for f in page.frames:
        try:
            if repeat_a[:18] in f.content():
                tframe = f
                break
        except Exception:
            continue
    if tframe is None:
        results(tag, "FAIL", "target text not in any frame")
        return False, None, None, None, None
    para = tframe.locator(f"text={repeat_a[:18]}").last
    try:
        para.wait_for(state="attached", timeout=10000)
    except Exception:
        results(tag, "FAIL", "target paragraph not attached")
        return False, None, None, None, None
    host_bb = page.locator(host_sel).bounding_box()
    if host_bb is None:
        results(tag, "FAIL", "host seam box unresolved")
        return False, None, None, None, None
    bb, turns, note = _vue_page_to_visible(page, para, host_bb)
    if bb is None:
        results(tag, "FAIL", f"paging: {note}")
        return False, None, None, None, None
    # 片段级行盒精化（vm 臂同款纪律：JS Range 量测用途，非代选）：巨列/
    # 大字号下段落跨列，union 包围盒横跨列间隙——mousedown 落隙则选区为空
    # （t09-vueiso9 实测）。取第一个与可视 seam 相交的行盒片段拖选。
    try:
        frags = tframe.evaluate(
            """(text) => {
                const walker = document.createTreeWalker(
                    document.body, NodeFilter.SHOW_TEXT);
                const hits = [];
                let n;
                while ((n = walker.nextNode())) {
                    let i = 0;
                    while ((i = n.data.indexOf(text, i)) >= 0) {
                        hits.push([n, i]); i += text.length;
                    }
                }
                if (hits.length < 2) return null;
                const [node, off] = hits[1];
                const end = node.data.indexOf('\\u3002', off);
                const r = document.createRange();
                r.setStart(node, off);
                r.setEnd(node, end > 0 ? end + 1 : off + text.length);
                const fe = frameElement
                    ? frameElement.getBoundingClientRect()
                    : {left: 0, top: 0};
                return [...r.getClientRects()].map(b => ({
                    x: b.left + fe.left, y: b.top + fe.top,
                    width: b.width, height: b.height}));
            }""", repeat_a[:18])
    except Exception:
        frags = None
    if frags:
        vis = [g for g in frags
               if g["width"] > 40 and g["height"] > 6
               and min(g["x"] + g["width"], host_bb["x"] + host_bb["width"])
               - max(g["x"], host_bb["x"]) > 60
               and min(g["y"] + g["height"], host_bb["y"] + host_bb["height"])
               - max(g["y"], host_bb["y"]) > 24]
        if vis:
            bb = vis[0]
    ix0 = max(bb["x"], host_bb["x"]) + 6
    ix1 = min(bb["x"] + bb["width"], host_bb["x"] + host_bb["width"]) - 6
    iy0 = max(bb["y"], host_bb["y"]) + 6
    iy1 = min(bb["y"] + bb["height"], host_bb["y"] + host_bb["height"]) - 6
    if ix1 - ix0 < 40 or iy1 - iy0 < 12:
        results(tag, "FAIL", "visible intersection too small")
        return False, None, None, None, None
    sx = ix0 + (ix1 - ix0) * 0.25
    sy = iy0 + (iy1 - iy0) * 0.35
    ex = ix0 + (ix1 - ix0) * 0.9
    ey = iy0 + (iy1 - iy0) * 0.9
    ev = None
    n_ev = page.evaluate("() => (window.__probe.events || []).length")
    page.mouse.move(sx, sy)
    page.mouse.down()
    page.mouse.move((sx + ex) / 2, (sy + ey) / 2, steps=8)
    page.mouse.move(ex, ey, steps=8)
    page.mouse.up()
    t0 = time.monotonic()
    while time.monotonic() - t0 < 5:
        evs = page.evaluate("() => window.__probe.events || []")
        if len(evs) > n_ev:
            ev = evs[-1]
            break
        time.sleep(0.4)
    if not ev:
        results(tag + ".drag-event", "FAIL", "no locator event after real drag (5s)")
        return False, None, None, None, None
    respj = ev["resp"]
    for _ in range(2):
        if isinstance(respj, str):
            try:
                respj = json.loads(respj)
            except Exception:
                break
    quote = ev["msg"]["text_quote"]
    occ = ev["msg"]["occurrence"]
    cfi = ev["msg"]["cfi"]
    vq = oracle_scan.verify_quote(quote, occ)
    ok = respj.get("accepted") is True and vq.get("ok")
    results(tag + ".drag-oracle", "PASS" if ok else "FAIL",
            f"accepted={respj.get('accepted')} occ={occ} oracle_ok={vq.get('ok')} "
            f"pos={vq.get('position')}")
    return ok, quote, occ, cfi, respj


def _vue_anchor_target(page, cfi):
    """把视口锚回目标 CFI（goTo=既定许可通道，N-03 恢复同款）：next() 只向
    前，扰动腿先锚定再扰动，避免视口已越过目标后 forward-only 翻页不可达
    （t09-vueiso2 实测 next() 在书尾失去位移）。"""
    try:
        page.evaluate("""async (cfi) => {
            try { await window.__probe.view.goTo(cfi); return 'ok'; }
            catch (e) { return 'err:' + e; }
        }""", cfi)
        page.wait_for_timeout(1200)
        return True
    except Exception:
        return False


def _run_vue_n05(page, results, oracle_scan, repeat_a, shot_dir, anchor_cfi):
    """N-05（vue 轨，T-09）：字体重排/翻页滚动/遮挡/隐藏再展示后，真实
    拖选仍命中指定原文。像素取证=整页截图解码（真实合成面）。"""
    sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "native")))
    from test_native_standalone_ui import scan_png_pixels, count_near
    os.makedirs(shot_dir, exist_ok=True)

    def _shot(name):
        p = os.path.join(shot_dir, name)
        page.screenshot(path=p)
        try:
            return scan_png_pixels(p)
        except Exception as e:  # noqa: BLE001
            results("N-05.pixel-decode", "FAIL", f"{name}: {repr(e)[:80]}")
            return None

    # ① 字体重排：章节 body 200% → 重排后**再锚回**（重排会把目标列位
    # 置整体移动，锚定必须落在扰动之后，forward-only 翻页才可达）→ 真实拖选
    moved = page.evaluate("""() => {
        const cs = window.__probe.view.renderer.getContents();
        for (const c of cs) {
            if (c.doc && c.doc.body) {
                const before = c.doc.body.style.fontSize;
                c.doc.body.style.fontSize = '200%';
                return before || '';
            }
        }
        return null;
    }""")
    if moved is None:
        results("N-05.reflow-move", "FAIL", "section body not reachable")
        return
    # body 字号变化不触发分页器重算（其 resize 观察的是容器而非内容字号，
    # 页表失真后 next() 定位越过段尾，t09-vueiso5/6/7 实测）——调 paginator
    # 自身 render() 全量重排（真实宿主版式变更后的同款内部路径），不经
    # 属性往返（gap 值会被当作显式覆盖污染后续页宽）。
    try:
        page.evaluate("""() => { const v = document.querySelector('foliate-view');
            const p = v.shadowRoot.querySelector('foliate-paginator');
            if (typeof p.render === 'function') { p.render(); return 'render'; }
            return 'no-render-fn'; }""")
        page.wait_for_timeout(1200)
    except Exception:
        pass
    stable = 0
    last_w = None
    for _ in range(16):
        w_now = page.evaluate(
            "() => { const v = document.querySelector('foliate-view');"
            " const p = v.shadowRoot.querySelector('foliate-paginator');"
            " const f = p.shadowRoot.querySelector('iframe');"
            " return f ? f.contentWindow.innerWidth : null; }")
        if last_w is not None and w_now == last_w:
            stable += 1
            if stable >= 2:
                break
        else:
            stable = 0
        last_w = w_now
        page.wait_for_timeout(700)
    if not _vue_anchor_target(page, "epubcfi(/6/2!/4/2)"):
        page.evaluate("""() => {
            const cs = window.__probe.view.renderer.getContents();
            for (const c of cs) { if (c.doc && c.doc.body) c.doc.body.style.fontSize = ''; }
            return 1;
        }""")
        results("N-05.reflow", "FAIL", "post-reflow goTo anchor failed")
        return
    # 锚到段首而非目标 CFI：goTo 目标 CFI 在重排后定位语义会落到段尾钳制
    # （t09-vueiso4..8 一致复现 x=-38422），段首 → 目标恒 forward 可达
    # （N-02 拖选链同路已证 20 轮可达）。
    _vue_drag_and_verify(page, results, oracle_scan, "N-05.reflow", repeat_a)
    page.evaluate("""() => {
        const cs = window.__probe.view.renderer.getContents();
        for (const c of cs) { if (c.doc && c.doc.body) c.doc.body.style.fontSize = ''; }
        return 1;
    }""")
    page.wait_for_timeout(800)

    # ② 翻页滚动：锚回 → next() 离开 → prev() 回（滚动位姿已变）→ 真实拖选
    _vue_anchor_target(page, anchor_cfi)
    page.evaluate("() => window.__probe.view.renderer.next()")
    page.wait_for_timeout(900)
    page.evaluate("() => window.__probe.view.renderer.prev()")
    page.wait_for_timeout(900)
    _vue_drag_and_verify(page, results, oracle_scan, "N-05.repage", repeat_a)

    # ③ 遮挡：先锚回目标 → 宿主页真实覆盖层（z-index 置顶纯色 div 盖住
    # remote-frame）→ 像素三段（before白/覆盖红/撤除白）→ 撤除后真实拖选
    _vue_anchor_target(page, anchor_cfi)
    host_bb = page.locator("[data-remote-frame]").bounding_box()
    cx = int(host_bb["x"] + host_bb["width"] / 2)
    cy = int(host_bb["y"] + host_bb["height"] / 2)
    px0 = _shot("n05-occ-before.png")
    n_red0 = count_near(px0, (255, 0, 0)) if px0 else -1
    page.evaluate("""() => {
        const d = document.createElement('div');
        d.id = 'probe-occluder';
        d.style.cssText = 'position:fixed;inset:0;background:#ff0000;z-index:9999';
        document.body.appendChild(d);
        return 1;
    }""")
    page.wait_for_timeout(500)
    px1 = _shot("n05-occ-during.png")
    n_red1 = count_near(px1, (255, 0, 0)) if px1 else -1
    results("N-05.occlusion-cover", "PASS" if n_red1 > 20000 and n_red1 > n_red0 else "FAIL",
            f"red_px before={n_red0} during={n_red1} (overlay must own pixels)")
    page.evaluate("() => { const d = document.getElementById('probe-occluder');"
                  " if (d) d.remove(); return 1; }")
    page.wait_for_timeout(500)
    px2 = _shot("n05-occ-after.png")
    n_red2 = count_near(px2, (255, 0, 0)) if px2 else -1
    results("N-05.occlusion-reveal", "PASS" if n_red2 < n_red1 / 10 else "FAIL",
            f"red_px after={n_red2}")
    _vue_drag_and_verify(page, results, oracle_scan, "N-05.occlusion", repeat_a)

    # ④ 隐藏→再展示：锚回 → display:none → foliate-view 真隐藏（无盒）→
    # 恢复 → 真实拖选重新命中
    _vue_anchor_target(page, anchor_cfi)
    page.evaluate("""() => {
        const h = document.querySelector('[data-remote-frame]');
        h.__probe_disp = h.style.display;
        h.style.display = 'none';
        return 1;
    }""")
    page.wait_for_timeout(600)
    gone = page.evaluate(
        "() => document.querySelector('[data-remote-frame] foliate-view')"
        " === null || document.querySelector('[data-remote-frame]').offsetParent === null")
    results("N-05.hideshow-hide", "PASS" if bool(gone) else "FAIL",
            "foliate-view box gone=" + str(gone))
    page.evaluate("""() => {
        const h = document.querySelector('[data-remote-frame]');
        h.style.display = h.__probe_disp || '';
        return 1;
    }""")
    page.wait_for_timeout(900)
    _vue_drag_and_verify(page, results, oracle_scan, "N-05.hideshow", repeat_a)


def _run_vue_n11(page, results, oracle_scan, data_dir, sid, true_quote, true_cfi):
    """N-11（vue 轨，T-09）：磁盘变异真实已存 locator → 原始 oracle 实红 +
    错 CFI 恢复落点异位（位置指纹，非文本可见性口径）→ 字节级还原 →
    oracle 绿 + 恢复命中。隔离 probe 数据目录，用户数据零污染。"""
    disk = os.path.join(data_dir, "probe", "locators", sid + ".json")
    if not os.path.exists(disk):
        results("N-11", "FAIL", "sidecar file missing: " + disk)
        return
    raw = open(disk, "rb").read()
    dj = json.loads(raw.decode("utf-8"))
    recs = dj.get("records", [])
    if not recs:
        results("N-11", "FAIL", "sidecar has no records")
        return
    mut_q = "零出现变异片段 probe-zero-occurrence-xyz"
    recs[-1]["locator"]["text_quote"] = mut_q
    with open(disk, "w", encoding="utf-8") as f:
        json.dump(dj, f, ensure_ascii=False)
    vq = oracle_scan.verify_quote(mut_q, 1)
    results("N-11.mutation-red", "PASS" if not vq.get("ok") else "FAIL",
            f"mutated quote -> oracle ok={vq.get('ok')} reason={vq.get('reason', '')[:40]}"
            " (must be red)")

    def _go_to(cfi):
        return page.evaluate("""async (cfi) => {
            try { await window.__probe.view.goTo(cfi); return 'ok'; }
            catch (e) { return 'err:' + e; }
        }""", cfi)

    def _last_loc():
        return page.evaluate(
            "() => { const l = window.__probe.view.lastLocation;"
            " return l ? String(l.cfi || '') : null; }")

    # 错 CFI 恢复落点异位（位置指纹判据，同 vm 臂口径）：投错 CFI 与真
    # CFI 的 lastLocation 必须不同——textContent 口径会被邻 section 预渲染
    # 文档污染（t09-vueiso2 实测假阴性），不可用。
    wrong_cfi = "epubcfi(/6/2!/4/2,/1:1,/1:5)"
    _go_to(wrong_cfi)
    page.wait_for_timeout(1500)
    loc_wrong = _last_loc()
    results("N-11.wrong-cfi-lands-elsewhere",
            "PASS" if (loc_wrong and loc_wrong != true_cfi) else "FAIL",
            f"goTo({wrong_cfi}) lastLocation={str(loc_wrong)[:50]!r} ≠ true={true_cfi[:40]!r}")
    # 字节级还原 → oracle 绿 + 恢复落点=真 CFI
    with open(disk, "wb") as f:
        f.write(raw)
    back = open(disk, "rb").read()
    results("N-11.restore-bytes", "PASS" if back == raw else "FAIL",
            f"bytes_restored={back == raw}")
    vq2 = oracle_scan.verify_quote(true_quote, 1)
    _go_to(true_cfi)
    page.wait_for_timeout(1500)
    loc_true = _last_loc()
    results("N-11.restore-green",
            "PASS" if (vq2.get("ok") and loc_true and loc_true != loc_wrong) else "FAIL",
            f"oracle_ok={vq2.get('ok')} lastLocation={str(loc_true)[:50]!r} ≠ wrong={str(loc_wrong)[:40]!r}")


def run_vue(out_dir, corpus_dir, oracle_scan, repeat_a, results):
    """N-02/V-02/V-03(vue) + V-06/V-07 HTTP 负控。results = record(case,outcome,detail)。"""
    from playwright.sync_api import sync_playwright

    data_dir = os.path.join(out_dir, "probe-data")
    reader_data = os.path.join(out_dir, "reader-data")
    for d in (data_dir, reader_data):
        shutil.rmtree(d, ignore_errors=True)
    assets_dir = os.environ.get("PROBE_ASSETS_DIR", "")
    if not os.path.isfile(os.path.join(assets_dir, "foliate-view.js")):
        results("N-02", "GAP", "engine assets missing: " + assets_dir)
        return

    epub = os.path.join(corpus_dir, "probe-alpha.epub")
    reader_inst = Instance(READER_ROOT, os.path.join(out_dir, "reader.log"),
                           {"AUTO_READER_DATA": reader_data})
    cons = None
    try:
        if not reader_inst.wait("http://127.0.0.1:17825/api/library/books"):
            results("N-02", "FAIL", "reader boot timeout")
            return
        r = http("POST", "http://127.0.0.1:17825/api/library/import",
                 {"path": epub.replace("\\", "/"), "author": "PLAN-026", "force": False},
                 timeout=120)
        s = json.dumps(r, ensure_ascii=False)
        if '"book_id"' not in s:
            results("N-02", "FAIL", "real import contract: " + s[:200])
            return
        books = http("GET", "http://127.0.0.1:17825/api/library/books")
        bl = books.get("books") if isinstance(books, dict) else books
        target = next((b for b in bl if b.get("format") == "epub"), None)
        if target is None:
            results("N-02", "FAIL", "no epub in library: " + json.dumps(bl, ensure_ascii=False)[:200])
            return
        bj = http("GET", "http://127.0.0.1:17825/api/library/books/" + target["book_id"])
        ident = {"book_id": bj["book_id"], "source_hash": bj["source_hash"],
                 "managed_path": str(bj["managed_path"]).replace("\\", "/"),
                 "title": bj.get("title", ""),
                 "size": os.path.getsize(bj["managed_path"])
                 if os.path.exists(bj["managed_path"]) else 0}
        results("N-02.reader-import", "PASS",
                f"book_id={ident['book_id'][:13]}… hash={str(ident['source_hash'])[:20]}… "
                f"managed={os.path.basename(ident['managed_path'])}")

        cons = Instance(APP_DIR, os.path.join(out_dir, "consumer.log"),
                        {"PROBE_DATA_DIR": data_dir, "PROBE_ASSETS_DIR": assets_dir})
        if not cons.wait("http://127.0.0.1:17827/api/probe/health"):
            results("N-02", "FAIL", "consumer backend boot timeout")
            return
        if not _wait_front():
            results("N-02", "FAIL", "consumer vite front not ready (60s)")
            return

        reg = http("POST", "http://127.0.0.1:17827/api/probe/register",
                   {"book_id": ident["book_id"], "source_hash": ident["source_hash"],
                    "managed_path": ident["managed_path"], "title": ident.get("title", ""),
                    "book_bytes": ident["size"]})
        if not reg.get("ok"):
            results("N-02", "FAIL", "register: " + json.dumps(reg, ensure_ascii=False)[:200])
            return
        sid = "vue-sess-" + str(int(time.time()))
        sess = http("POST", "http://127.0.0.1:17827/api/probe/session",
                    {"session_id": sid, "book_id": ident["book_id"],
                     "source_hash": ident["source_hash"], "engine": ENGINE_REVISION})
        if not sess.get("ok"):
            results("N-02", "FAIL", "session: " + json.dumps(sess)[:160])
            return

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            ready, load_ms = mount_and_wait(page, ident, sid)
            if not ready:
                results("N-02", "FAIL", "engine not mounted (title=" + page.title() + ")")
                return
            spine = page.evaluate("() => window.__probe.book.sections.length")
            results("N-02.engine-mount", "PASS",
                    f"engine={ENGINE_REVISION} spine={spine} loadMs={load_ms} (budget 15000)")
            if load_ms > 15000:
                results("N-02.engine-load-budget", "FAIL", f"loadMs={load_ms}")
            in_host = page.evaluate(
                "() => !!document.querySelector('[data-remote-frame] foliate-view')")
            results("N-02.surface-in-host", "PASS" if in_host else "FAIL",
                    "foliate-view inside [data-remote-frame]=" + str(in_host))
            page.wait_for_timeout(1500)

            # ── V-02：真实拖选第二处重复句（不代选；跨行路径）──
            # foliate paginator 以 iframe 隔离章节：text= 定位不跨 iframe，
            # 需按 frame 搜索后取页面级坐标。
            tframe = None
            t0 = time.monotonic()
            while time.monotonic() - t0 < 10 and tframe is None:
                for f in page.frames:
                    try:
                        if repeat_a[:18] in f.content():
                            tframe = f
                            break
                    except Exception:
                        continue
                if tframe is None:
                    time.sleep(1)
            if tframe is None:
                results("N-02", "FAIL", "target text not found in any frame (10s)")
                return
            para = tframe.locator(f"text={repeat_a[:18]}").last
            para.wait_for(state="attached", timeout=10000)
            # 分栏渲染：第二处出现可能在可视列之外——真实翻页直至相交
            # （共享分页驱动：位移进度守卫 + 永不相交具名失败，见
            # _vue_page_to_visible；巨列形态需 ~20 轮，旧 12 轮不可达）。
            host_bb0 = page.locator("[data-remote-frame]").bounding_box()
            if host_bb0 is None:
                results("N-02", "FAIL", "host seam box unresolved")
                return
            bb, turns, pnote = _vue_page_to_visible(page, para, host_bb0)
            if bb is None:
                results("N-02", "FAIL", f"paging: {pnote}")
                return
            results("N-02.target-visible", "PASS",
                    f"2nd occurrence visible after {turns} real page turns")
            # 分栏渲染下目标段可能部分位于可视区外：拖选限制在
            # remote-frame 可视交集内（真实拖选不代选，选区为可见子串）。
            host_bb = page.locator("[data-remote-frame]").bounding_box()
            ix0 = max(bb["x"], host_bb["x"]) + 6
            ix1 = min(bb["x"] + bb["width"], host_bb["x"] + host_bb["width"]) - 6
            iy0 = max(bb["y"], host_bb["y"]) + 6
            iy1 = min(bb["y"] + bb["height"], host_bb["y"] + host_bb["height"]) - 6
            sx = ix0 + (ix1 - ix0) * 0.25
            sy = iy0 + (iy1 - iy0) * 0.35
            ex = ix0 + (ix1 - ix0) * 0.9
            ey = iy0 + (iy1 - iy0) * 0.9
            page.mouse.move(sx, sy)
            page.mouse.down()
            page.mouse.move((sx + ex) / 2, (sy + ey) / 2, steps=8)
            page.mouse.move(ex, ey, steps=8)
            page.mouse.up()
            ev = None
            t0 = time.monotonic()
            while time.monotonic() - t0 < 5:
                evs = page.evaluate("() => window.__probe.events")
                if evs:
                    ev = evs[-1]
                    break
                time.sleep(0.4)
            if not ev:
                results("N-02", "FAIL", "no locator event after real drag (5s)")
                return
            respj = ev["resp"]
            for _ in range(2):
                if isinstance(respj, str):
                    try:
                        respj = json.loads(respj)
                    except Exception:
                        break
            accepted = respj.get("accepted") is True
            results("N-02.real-drag-event", "PASS" if accepted else "FAIL",
                    "resp=" + json.dumps(respj, ensure_ascii=False)[:200])
            quote_sel = ev["msg"]["text_quote"]
            occ_eng = ev["msg"]["occurrence"]
            cfi_sel = ev["msg"]["cfi"]
            vq = oracle_scan.verify_quote(quote_sel, occ_eng)
            results("N-02.quote-oracle", "PASS" if vq.get("ok") else "FAIL",
                    f"occ={occ_eng} pos={vq.get('position')} occurrences={vq.get('occurrences')}")
            results("N-02.cfi-present", "PASS" if str(cfi_sel).startswith("epubcfi") else "FAIL",
                    "cfi=" + str(cfi_sel)[:60])
            side = http("GET", f"http://127.0.0.1:17827/api/probe/locators?session_id={sid}")
            n_rec = len(side.get("sidecar", {}).get("records", [])) if side.get("found") else 0
            results("N-02.sidecar-http", "PASS" if n_rec >= 1 else "FAIL", f"records={n_rec}")
            disk = os.path.join(data_dir, "probe", "locators", sid + ".json")
            ok_disk = os.path.exists(disk) and quote_sel in open(disk, encoding="utf-8").read()
            results("N-02.sidecar-disk", "PASS" if ok_disk else "FAIL", disk)
            # 图/脚注在 ch2：分页器按需装载（邻章预渲染不再保证）——放在
            # 拖选链之后，真实翻页（许可通道）到图所在章再断言；向后翻页
            # 不可达（next() 只向前），不能置于拖选前。
            def _find_img_and_note():
                return page.evaluate("""() => {
                    const cs = window.__probe.view.renderer.getContents();
                    let im = null, note = false;
                    for (const c of cs) {
                        if (!im) {
                            const i = c.doc.querySelector('img');
                            if (i) im = i;
                        }
                        if (c.doc.body && c.doc.body.textContent.includes('章内注')) note = true;
                    }
                    return {found: !!im, ok: !!im && im.complete && im.naturalWidth > 0,
                            w: im ? im.naturalWidth : 0, h: im ? im.naturalHeight : 0, note};
                }""")
            img_state = _find_img_and_note()
            turns_img = 0
            while not (img_state.get("found") and img_state.get("note")) and turns_img < 8:
                page.evaluate("() => window.__probe.view.renderer.next()")
                page.wait_for_timeout(900)
                turns_img += 1
                img_state = _find_img_and_note()
            results("N-02.image-decode", "PASS" if img_state.get("ok") else "FAIL",
                    f"natural={img_state.get('w')}x{img_state.get('h')} "
                    f"after {turns_img} page turns (expect 96x64)")
            results("N-02.footnote-present", "PASS" if img_state.get("note") else "FAIL",
                    "章内注 visible=" + str(img_state.get("note"))
                    + f" (after {turns_img} page turns)")
            # ── N-05（vue 轨，T-09）：几何/遮挡/隐藏后真实拖选仍命中 ──
            try:
                _run_vue_n05(page, results, oracle_scan, repeat_a,
                             os.path.join(out_dir, "shots"), cfi_sel)
            except Exception as e:  # noqa: BLE001
                results("N-05", "FAIL", "vue geometry gate exception: " + repr(e)[:140])
            browser.close()

        # ── V-03：冷重启恢复 ──
        cons.stop()
        cons = None
        time.sleep(2)
        cons = Instance(APP_DIR, os.path.join(out_dir, "consumer2.log"),
                        {"PROBE_DATA_DIR": data_dir, "PROBE_ASSETS_DIR": assets_dir})
        if not cons.wait("http://127.0.0.1:17827/api/probe/health"):
            results("N-03", "FAIL", "consumer restart timeout")
            return
        if not _wait_front():
            results("N-03", "FAIL", "consumer vite front not ready after restart")
            return
        sid2 = sid + "r"
        http("POST", "http://127.0.0.1:17827/api/probe/session",
             {"session_id": sid2, "book_id": ident["book_id"],
              "source_hash": ident["source_hash"], "engine": ENGINE_REVISION})
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            ready, _ = mount_and_wait(page, ident, sid2)
            if not ready:
                results("N-03", "FAIL", "engine not mounted after restart")
                return
            page.evaluate("() => { window.__probe.target = %s; return 1; }"
                          % json.dumps(quote_sel))
            goto_ok = False
            err = ""
            t0 = time.monotonic()
            while time.monotonic() - t0 < 30:
                r = page.evaluate("""async (cfi) => {
                    try { await window.__probe.view.goTo(cfi); return 'ok'; }
                    catch (e) { return 'err:' + e; }
                }""", cfi_sel)
                if r == "ok":
                    txt = page.evaluate("""() => {
                        const cs = window.__probe.view.renderer.getContents();
                        for (const c of cs) {
                            if (c.doc.body && c.doc.body.textContent.includes(window.__probe.target)) return true;
                        }
                        return false;
                    }""")
                    if txt:
                        goto_ok = True
                        break
                err = r
                time.sleep(1.5)
            results("N-03.cold-restart-restore", "PASS" if goto_ok else "FAIL",
                    f"goTo={err or 'ok'} target-visible={goto_ok} (deadline 30s)")
            # ── N-11（vue 轨，T-09）：磁盘变异红→还原绿（同一视图实例内）──
            try:
                _run_vue_n11(page, results, oracle_scan, data_dir, sid,
                             quote_sel, cfi_sel)
            except Exception as e:  # noqa: BLE001
                results("N-11", "FAIL", "vue mutation gate exception: " + repr(e)[:140])
            browser.close()

        # ── V-06/V-07 HTTP 负控 ──
        n0 = len(http("GET", f"http://127.0.0.1:17827/api/probe/locators?session_id={sid}")
                 .get("sidecar", {}).get("records", []))
        negatives = [
            ("N-09.bad-session", {"session_id": "evil-sess-9999"}, "rejected_bad_session"),
            ("N-09.bad-document", {"book_id": "uuid-OTHER"}, "rejected_bad_document"),
            ("N-09.stale-seq", {"seq": 1}, "rejected_stale_seq"),
            ("N-09.bad-schema", {"schema_version": 2}, "rejected_bad_schema"),
        ]
        for case, override, want in negatives:
            msg = {"schema_version": 1, "kind": "locator_select", "session_id": sid,
                   "book_id": ident["book_id"], "source_hash": ident["source_hash"],
                   "engine": ENGINE_REVISION, "resource_href": "ch1.xhtml",
                   "resource_index": 0, "cfi": "epubcfi(/6/4)", "range_cfi": "",
                   "text_quote": quote_sel, "occurrence": 1,
                   "context_before": "", "context_after": "", "seq": 99, "ts": 1}
            msg.update(override)
            r = http("POST", "http://127.0.0.1:17827/api/probe/locator", msg)
            okn = r.get("accepted") is False and r.get("reason") == want
            results(case, "PASS" if okn else "FAIL", json.dumps(r, ensure_ascii=False)[:140])
        n1 = len(http("GET", f"http://127.0.0.1:17827/api/probe/locators?session_id={sid}")
                 .get("sidecar", {}).get("records", []))
        results("N-09.zero-disk-on-reject", "PASS" if n1 == n0 else "FAIL",
                f"before={n0} after={n1}")
        try:
            urllib.request.urlopen(
                "http://127.0.0.1:17827/api/probe/document/uuid-NOPE/file", timeout=10)
            results("N-09.unregistered-404", "FAIL", "served unregistered doc")
        except urllib.error.HTTPError as e:
            results("N-09.unregistered-404", "PASS" if e.code == 404 else "FAIL",
                    f"code={e.code}")
        try:
            urllib.request.urlopen(
                "http://127.0.0.1:17827/api/probe/asset/..%2F..%2Fprobe-alpha.epub", timeout=10)
            results("N-09.path-escape", "FAIL", "served escape path")
        except urllib.error.HTTPError as e:
            results("N-09.path-escape", "PASS" if e.code in (400, 403, 404) else "FAIL",
                    f"code={e.code}")
        except Exception as e:  # noqa: BLE001
            results("N-09.path-escape", "PASS", "transport refused: " + repr(e)[:80])

        # ── V-09：内容损坏后的错锚（同 session，受管内容被改写）──
        # 复制 alpha 并把 ch1 正文「十七」改写为「十八」（zip 级精准替换），
        # 注册为独立文档；对改写书提交原句 quote 必须被原文核验明确拒绝
        # （quote_not_found，不静默换第一处、零落盘）；改写后句对照仍接受。
        import zipfile as _zf
        mutated = os.path.join(out_dir, "probe-mutated.epub")
        try:
            with _zf.ZipFile(epub) as zin, _zf.ZipFile(mutated, "w") as zout:
                for item in zin.infolist():
                    data = zin.read(item.filename)
                    if item.filename.endswith(".xhtml"):
                        data = data.decode("utf-8").replace("十七", "十八").encode("utf-8")
                    zout.writestr(item, data)
            msize = os.path.getsize(mutated)
            r = http("POST", "http://127.0.0.1:17827/api/probe/register",
                      {"book_id": "uuid-MUT", "source_hash": "mut-hash-01",
                       "managed_path": mutated.replace("\\", "/"), "title": "mutated",
                       "book_bytes": msize})
            if not r.get("ok"):
                results("N-09.mutated-register", "FAIL", json.dumps(r, ensure_ascii=False)[:160])
                return
            sid9 = sid + "m"
            http("POST", "http://127.0.0.1:17827/api/probe/session",
                  {"session_id": sid9, "book_id": "uuid-MUT",
                   "source_hash": "mut-hash-01", "engine": ENGINE_REVISION})
            q_orig = repeat_a
            q_mut = repeat_a.replace("十七", "十八")
            rj = http("POST", "http://127.0.0.1:17827/api/probe/locator",
                       {"schema_version": 1, "kind": "locator_select", "session_id": sid9,
                        "book_id": "uuid-MUT", "source_hash": "mut-hash-01",
                        "engine": ENGINE_REVISION, "resource_href": "ch1.xhtml",
                        "resource_index": 0, "cfi": "epubcfi(/6/4)", "range_cfi": "",
                        "text_quote": q_orig, "occurrence": 1,
                        "context_before": "", "context_after": "", "seq": 1, "ts": 1})
            ok_rej = rj.get("accepted") is False and                 "quote_not_found" in json.dumps(rj, ensure_ascii=False)
            results("N-09.stale-quote-rejected", "PASS" if ok_rej else "FAIL",
                    json.dumps(rj, ensure_ascii=False)[:160])
            side9 = http("GET", f"http://127.0.0.1:17827/api/probe/locators?session_id={sid9}")
            results("N-09.zero-disk-on-stale",
                    "PASS" if not side9.get("found") else "FAIL",
                    "sidecar found=" + str(side9.get("found")))
            rj2 = http("POST", "http://127.0.0.1:17827/api/probe/locator",
                        {"schema_version": 1, "kind": "locator_select", "session_id": sid9,
                         "book_id": "uuid-MUT", "source_hash": "mut-hash-01",
                         "engine": ENGINE_REVISION, "resource_href": "ch1.xhtml",
                         "resource_index": 0, "cfi": "epubcfi(/6/4)", "range_cfi": "",
                         "text_quote": q_mut, "occurrence": 1,
                         "context_before": "", "context_after": "", "seq": 2, "ts": 2})
            results("N-09.mutated-control-accepted",
                    "PASS" if rj2.get("accepted") is True else "FAIL",
                    json.dumps(rj2, ensure_ascii=False)[:160])
        except Exception as e:  # noqa: BLE001
            results("N-09", "FAIL", repr(e)[:160])
    finally:
        if cons:
            cons.stop()
        reader_inst.stop()


def _wait_front(deadline_s=60):
    t0 = time.monotonic()
    while time.monotonic() - t0 < deadline_s:
        try:
            with urllib.request.urlopen("http://localhost:17826/", timeout=3) as r2:
                if r2.status == 200:
                    return True
        except Exception:
            time.sleep(1.5)
    return False
