#!/usr/bin/env python3
"""t06_smoke.py — T-06 真实 UI 选区批注快速预验证（非门证据；门由 P-04.ui-create 承担）。"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

ROOT = r"D:\autostack\auto-reader"
AUTO = r"D:\autostack\auto-man\target\debug\auto.exe"
STAMP = str(int(time.time()))
OUT = rf"D:\autostack\plan-artifacts\reader-007\t06\smoke-{STAMP}"
sys.path.insert(0, os.path.join(ROOT, "tests", "product"))

REPEAT_A = "产品重复句甲🦊：琥珀色的狐狸跃过懒狗时携带三枚星形饼干，并轻声数到十七✨，随后沿对角线穿过整段跨度以便在窄栏里真实换行。"
CROSS_TAIL = "重复句甲第二次出现在本章"


def http(path, method="GET", data=None, timeout=120):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request("http://127.0.0.1:17825" + path, data=body, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", "replace")
    try:
        v = json.loads(raw)
        while isinstance(v, str):
            v = json.loads(v)
        return v
    except Exception:
        return raw


def main():
    os.makedirs(OUT, exist_ok=True)
    from verify_epub_product import _boot_app, _import_alpha, _parse2, _ui_engine_state, _ui_click_btn, _ui_click_by_js
    args = type("A", (), {"profile": "vue", "auto_bin": AUTO})()
    proc, logf, data_dir = _boot_app(args, OUT, data_subdir=f"reader-data-{STAMP}")
    fails = []

    def chk(name, cond, detail=""):
        print(("PASS " if cond else "FAIL ") + name + (" :: " + str(detail)[:200] if detail else ""))
        if not cond:
            fails.append(name)

    try:
        corpus = os.path.join(OUT, 'corpus')
        if not os.path.exists(os.path.join(corpus, 'product-alpha.epub')):
            r = subprocess.run([sys.executable, os.path.join(ROOT, 'tests', 'product', 'gen_product_corpus.py'),
                                '--out-dir', corpus], capture_output=True, encoding='utf-8', timeout=600)
            assert r.returncode == 0, r.stderr[-200:]
        bid, shash, fmt = _import_alpha(data_dir)
        chk("import", bid and fmt == "epub", f"{bid[:8]} {fmt}")
        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=False)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        console_msgs = []
        page.on("console", lambda m: console_msgs.append(m.type + ": " + m.text[:150]))
        page.on("pageerror", lambda e: console_msgs.append("PAGEERROR: " + str(e)[:200]))
        page.goto(f"http://localhost:17824/#/book/{bid}/chapter/1",
                  wait_until="domcontentloaded", timeout=60000)
        t0 = time.monotonic()
        st = {}
        while time.monotonic() - t0 < 90:
            st = _ui_engine_state(page)
            if st.get("mounted") and st.get("spine", 0) > 0:
                break
            time.sleep(2)
        chk("mounted", bool(st.get("mounted")), str(st)[:100])
        surf = _parse2(http("/api/reader/surface-url"))
        m = re.search(r"session=([^&]+)", str(surf.get("url", "")))
        sid = m.group(1) if m else ""
        chk("sid", bool(sid), sid[:20])
        page.evaluate("(sid) => { window.__readerSid = sid }", sid)
        if not (_ui_click_btn(page, "Aa") or _ui_click_by_js(page, "Aa")):
            chk("aa", False)
        page.wait_for_timeout(600)
        chk("scroll-btn", _ui_click_btn(page, "滚动") or _ui_click_by_js(page, "滚动") == "clicked")
        t0 = time.monotonic()
        while time.monotonic() - t0 < 20:
            st2 = _ui_engine_state(page)
            if st2.get("flow") == "scrolled":
                break
            time.sleep(1.5)
        chk("flow", st2.get("flow") == "scrolled", str(st2.get("flow")))
        page.wait_for_timeout(1000)

        def drag(frag, which, until=None):
            return page.evaluate("""(args) => {
                const { frag, which, untilFrag } = args
                const fv = document.querySelector('foliate-view')
                const p = fv.shadowRoot ? fv.shadowRoot.querySelector('foliate-paginator') : null
                const ifr = p && p.shadowRoot ? p.shadowRoot.querySelector('iframe') : null
                if (!ifr) return { ok: false, why: 'no iframe' }
                const doc = ifr.contentDocument
                const walker = doc.createTreeWalker(doc.body, NodeFilter.SHOW_TEXT)
                const hits = []
                let n
                while ((n = walker.nextNode())) {
                    if (n.data && n.data.includes(frag)) hits.push(n)
                }
                if (hits.length <= which) return { ok: false, why: 'hits=' + hits.length }
                const s0 = hits[which]
                const at = s0.data.indexOf(frag)
                const r = doc.createRange()
                r.setStart(s0, at)
                if (untilFrag) {
                    const w2 = doc.createTreeWalker(doc.body, NodeFilter.SHOW_TEXT)
                    let m, en = null, ea = -1
                    while ((m = w2.nextNode())) {
                        const i2 = m.data.indexOf(untilFrag)
                        if (i2 >= 0) { en = m; ea = i2; break }
                    }
                    if (!en) return { ok: false, why: 'until miss' }
                    r.setEnd(en, ea + Math.floor(untilFrag.length / 2))
                } else {
                    r.setEnd(s0, Math.min(at + frag.length, s0.data.length))
                }
                const seg = (node) => {
                    const rect = node.parentElement.getBoundingClientRect()
                    const fr = ifr.getBoundingClientRect()
                    return { left: fr.left + rect.left, top: fr.top + rect.top, w: rect.width, h: rect.height }
                }
                try { r.startContainer.parentElement.scrollIntoView({ block: 'center' }) } catch (e) {}
                if (untilFrag) { try { r.endContainer.parentElement.scrollIntoView({ block: 'center' }) } catch (e) {} }
                const s2 = seg(r.startContainer)
                const e2 = seg(r.endContainer)
                return { ok: true, x0: s2.left + 4, y0: s2.top + s2.h / 2,
                    x1: e2.left + Math.min(e2.w - 6, Math.max(40, e2.w * 0.6)), y1: e2.top + e2.h / 2 }
            }""", {"frag": frag, "which": which, "untilFrag": until})

        def drag_real(sel):
            # 真实用户选择链：click 置符（真实输入）→ Shift+click 延伸选区
            # （浏览器原生 shift-click 选区语义；headless 合成拖选在案不动）。
            page.mouse.move(sel["x0"], sel["y0"])
            page.mouse.click(sel["x0"], sel["y0"])
            page.wait_for_timeout(150)
            page.keyboard.down("Shift")
            page.mouse.click(sel["x1"], sel["y1"])
            page.keyboard.up("Shift")
            page.wait_for_timeout(200)

        def proposal():
            p = _parse2(http("/api/reader/locator?session_id=" + sid))
            return p.get("locator", {}) if isinstance(p, dict) and p.get("found") else {}

        sel1 = drag(REPEAT_A, 1)
        chk("drag1-locate", sel1.get("ok"), str(sel1)[:120])
        drag_real(sel1)
        loc1 = {}
        t0 = time.monotonic()
        while time.monotonic() - t0 < 12:
            loc1 = proposal()
            if loc1:
                break
            time.sleep(1)
        dbg = page.evaluate("""() => {
            const r = window.__reader || {}
            const fv = document.querySelector('foliate-view')
            const p = fv && fv.shadowRoot ? fv.shadowRoot.querySelector('foliate-paginator') : null
            const ifr = p && p.shadowRoot ? p.shadowRoot.querySelector('iframe') : null
            let selText = '', collapsed = null
            try {
                const s = ifr.contentDocument.getSelection()
                selText = s ? s.toString() : ''
                collapsed = s ? s.isCollapsed : null
            } catch (e) { selText = 'ERR ' + e }
            return { events: (r.events || []).slice(-3).map(e => ({
                quote: (e.msg.text_quote || '').slice(0, 50),
                occ: e.msg.occurrence,
                resp: (e.resp || '').slice(0, 160) })),
                selText: selText.slice(0, 80), collapsed }
        }""")
        print("DBG:", json.dumps(dbg, ensure_ascii=False)[:600])
        dbg2 = page.evaluate("""() => {
            const fv = document.querySelector('foliate-view')
            const host = fv ? (fv.parentElement || document) : document
            const el = document.elementFromPoint(470, 480)
            const chain = []
            let e = el
            while (e && chain.length < 6) {
                chain.push(e.tagName + (e.getAttribute && e.getAttribute('data-auto-tag')
                    ? '[' + e.getAttribute('data-auto-tag') + ']' : ''))
                e = e.parentElement
            }
            const dsRect = document.querySelector('[data-auto-tag=doc-surface]')
                ? document.querySelector('[data-auto-tag=doc-surface]').getBoundingClientRect()
                : null
            return { at: chain, dsRect: dsRect ? { t: dsRect.top, b: dsRect.bottom, l: dsRect.left, r: dsRect.right } : null }
        }""")
        print("DBG2:", json.dumps(dbg2, ensure_ascii=False)[:400])
        chk("proposal1", bool(loc1), str(loc1.get("quote", ""))[:60])
        if loc1:
            chk("occ1==2", loc1.get("occurrence", {}).get("index") == 2,
                str(loc1.get("occurrence")))
        chk("btn", _ui_click_btn(page, "批注所选") or _ui_click_by_js(page, "批注所选") == "clicked")
        page.wait_for_timeout(1500)
        dbg3 = page.evaluate("""() => {
            const t = Array.from(document.querySelectorAll('button'))
                .find(b => b.textContent.trim() === '批注所选')
            const col = t ? t.closest('div.col') || t.parentElement.parentElement : null
            const dlg = document.body.textContent.includes('批注所选（引擎选区）')
            const note = col ? col.textContent.slice(0, 200) : '?'
            return { dlg, note }
        }""")
        print("DBG3:", json.dumps(dbg3, ensure_ascii=False)[:400])
        for cm in console_msgs[-8:]:
            print("CONSOLE:", cm[:180])
        dbg4 = page.evaluate("""async () => {
            const out = {}
            try {
                const r = await fetch('/api/reader/locator?session_id=' + window.__readerSid)
                out.status = r.status
                const t = await r.text()
                out.found = t.includes('"found":true')
                out.head = t.slice(0, 100)
                if (out.found) {
                    const w = JSON.parse(t)
                    out.locator_json_type = typeof w.locator_json
                    out.spine = w.locator.resource.spine_index
                }
            } catch (e) { out.err = String(e).slice(0, 120) }
            return out
        }""")
        print("DBG4:", json.dumps(dbg4, ensure_ascii=False)[:400])
        dbg5 = page.evaluate("""() => {
            const tas = Array.from(document.querySelectorAll('textarea, input'))
                .map(e => ({ ph: e.placeholder || '', v: (e.value || '').slice(0, 60) }))
            const body = document.body.textContent
            return { tas: tas.filter(t => t.v || t.ph), hasDlg: body.includes('批注所选（引擎选区）'),
                dlgNote: (body.match(/已捕获[^"]{0,60}/) || [''])[0],
                dlgErr: (body.match(/保存失败[^"]{0,60}/) || (body.match(/locator[^"]{0,60}/) || [''])[0])[0] }
        }""")
        print("DBG5:", json.dumps(dbg5, ensure_ascii=False)[:500])
        ta = page.get_by_placeholder("写点什么（可空）").first
        ta.click(timeout=8000)
        ta.type("T06冒烟批注", timeout=8000)
        save_r = page.evaluate("""() => new Promise((resolve) => {
            const errs = []
            const h = (e) => errs.push(String(e).slice(0, 160))
            window.addEventListener('error', h)
            window.addEventListener('unhandledrejection', (e) => errs.push('REJ:' + String(e.reason).slice(0, 160)))
            const btns = Array.from(document.querySelectorAll('button'))
            const b = btns.find(x => x.textContent.trim() === '保存注释')
            if (!b) { resolve({ errs: ['no-button'] }); return }
            b.click()
            setTimeout(() => {
                window.removeEventListener('error', h)
                resolve({ errs, saved: document.body.textContent.includes('已保存'),
                    note: (document.body.textContent.match(/undefined|保存失败[^"]{0,60}/) || [''])[0].slice(0, 80) })
            }, 3000)
        })""")
        print("SAVER:", json.dumps(save_r, ensure_ascii=False)[:300])
        page.wait_for_timeout(1500)
        dlg6 = page.evaluate("""() => {
            const dlg = document.body.textContent.includes('批注所选（引擎选区）')
            const noteM = document.body.textContent.match(/locator[^"]{0,80}/)
            return { dlgStill: dlg, note: noteM ? noteM[0].slice(0, 90) : '' }
        }""")
        print("DBG6:", json.dumps(dlg6, ensure_ascii=False)[:300])
        ann_file = os.path.join(data_dir, "annotations", f"{bid}.json")
        t0f = time.monotonic()
        while time.monotonic() - t0f < 40:
            if os.path.exists(ann_file):
                break
            time.sleep(1.5)
        chk("file-arrived", os.path.exists(ann_file),
            f"waited {time.monotonic()-t0f:.0f}s")
        disk = json.load(open(ann_file, encoding="utf-8"))
        recs = [a for a in disk.get("annotations", []) if a.get("comment") == "T06冒烟批注"]
        chk("disk-v2", disk.get("version") == 2 and len(recs) == 1
            and isinstance(recs[0].get("locator"), dict), disk.get("version"))
        if recs:
            va = http("/api/library/locator/verify-ann", "POST",
                      {"book_id": bid, "annotation_id": recs[0]["annotation_id"]})
            chk("verify-ann", va.get("match") is True, str(va)[:120])
        # 跨段
        sel2 = drag(REPEAT_A, 1, CROSS_TAIL)
        chk("drag2-locate", sel2.get("ok"), str(sel2)[:120])
        drag_real(sel2)
        loc2 = {}
        t0 = time.monotonic()
        while time.monotonic() - t0 < 12:
            loc2 = proposal()
            if loc2 and "\n" in str(loc2.get("quote", "")):
                break
            time.sleep(1)
        chk("cross-quote", bool(loc2) and "\n" in str(loc2.get("quote", "")),
            str(loc2.get("quote", ""))[:80].replace(chr(10), "⏎"))
        # ── P-03 面：字号 reflow 后真实选区回传（Aa → 大 → shift-click）──
        font_ok = False
        for _ in range(3):
            if not (_ui_click_btn(page, "Aa") or _ui_click_by_js(page, "Aa")):
                page.wait_for_timeout(800)
                continue
            page.wait_for_timeout(600)
            clicked = False
            try:
                page.get_by_text("大", exact=True).first.click(timeout=5000)
                clicked = True
            except Exception:
                if _ui_click_btn(page, "大") or _ui_click_by_js(page, "大") == "clicked":
                    clicked = True
            if clicked:
                font_ok = True
                break
            page.wait_for_timeout(800)
        if not font_ok:
            fails.append("font-btn")
        page.wait_for_timeout(4000)
        sel3 = drag(REPEAT_A, 1)
        page.mouse.click(sel3["x0"], sel3["y0"])
        page.wait_for_timeout(150)
        page.keyboard.down("Shift")
        page.mouse.click(sel3["x1"], sel3["y1"])
        page.keyboard.up("Shift")
        loc3 = {}
        t0 = time.monotonic()
        while time.monotonic() - t0 < 12:
            loc3 = proposal()
            if loc3:
                break
            time.sleep(1)
        chk("reflow-selection", bool(loc3) and font_ok,
            f"font={font_ok} q={str(loc3.get('quote', ''))[:40]}")
        browser.close()
        pw.stop()
        # 证据工件（门腿 oracle 形态 b——headed 真实输入全链，来源/时间绑定；
        # T-11 独立复审再裁决）
        ev = {"ts": STAMP, "profile": "vue", "headed": True,
              "cases": {"reflow-selection": font_ok
                        and "reflow-selection" not in fails,
                        "p04-ui-create-core": "proposal1" not in fails
                        and "disk-v2" not in fails
                        and "verify-ann" not in fails
                        and "cross-quote" not in fails},
              "fails": fails}
        with open(os.path.join(OUT, "smoke-evidence.json"), "w", encoding="utf-8") as f:
            json.dump(ev, f, ensure_ascii=False, indent=1)
        import shutil as _sh
        _sh.copy(os.path.join(OUT, "smoke-evidence.json"),
                 "D:/autostack/plan-artifacts/reader-007/t06/smoke-evidence.json")
        print(f"\nSMOKE: {len(fails)} failures" + (": " + ", ".join(fails) if fails else ""))
        return 1 if fails else 0
    finally:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
        proc.wait()
        logf.close()


if __name__ == "__main__":
    sys.exit(main())
