// engine-adapter.js — READER-007 产品引擎 adapter（T-03 固化，消费 /api/reader/*）。
// 挂载点：正式 reading_page 的 doc-surface 引擎表面（VM 原生 WebView2 / vue 轨
// 宿主容器）。引擎：foliate-js fork@3d794195（应用自有受管资产同源装载）。
// 回传：选区 → 真实 DOM range → view.getCFI → 产品消息 v1 → 页面 fetch 通道
// → .at 消费 handler（身份由消费端对受管原文核验，不信任引擎自述）。
// 与 029 探针 adapter 同构；所有服务 URL 经 opts 注入（asset/document/locator
// 均走正式 /api/reader/*），无硬编码 probe 路径。

import { makeBook } from './foliate-view.js'

const ENGINE_REVISION = 'foliate-js@3d794195'

async function countOccurrences(book, quote) {
    // 引擎侧出现序：按 spine 序逐章 createDocument 取正文文本滑窗计数。
    let count = 0
    let first = null // {index, offsetInText}
    for (let i = 0; i < book.sections.length; i++) {
        const s = book.sections[i]
        if (!s || !s.createDocument) continue
        let text = ''
        try {
            const doc = await s.createDocument()
            text = doc.body ? doc.body.textContent : ''
        } catch (e) { continue }
        let pos = 0
        while (true) {
            const at = text.indexOf(quote, pos)
            if (at < 0) break
            count++
            if (!first) first = { index: i, offsetInText: at }
            pos = at + 1
        }
    }
    return { count, first }
}

export async function mountProbe(opts) {
    const {
        host,
        documentUrl,
        locatorUrl,
        sessionId,
        bookId,
        sourceHash,
        onStatus,
    } = opts
    const say = m => { try { onStatus(m) } catch (e) { /* noop */ } }

    say('fetching document bytes…')
    const resp = await fetch(documentUrl)
    if (!resp.ok) throw new Error('document fetch failed: ' + resp.status)
    const blob = await resp.blob()
    const file = new File([blob], 'product.epub', { type: 'application/epub+zip' })

    say('makeBook (foliate-js)…')
    const book = await makeBook(file)

    say('mounting foliate-view into engine surface…')
    const view = document.createElement('foliate-view')
    view.style.width = '100%'
    view.style.height = '100%'
    host.appendChild(view)

    const t0 = performance.now()
    await view.open(book)
    await view.init({ showTextStart: false })
    const loadMs = Math.round(performance.now() - t0)

    // 引擎身份锚：引擎对象与 revisions 暴露给驱动/检查面。
    window.__reader = { view, book, engine: ENGINE_REVISION, events: [], loadMs }

    say('engine loaded in ' + loadMs + 'ms, spine=' + book.sections.length)

    // 键盘可达接缝（029 T-05 继承）：foliate-js 无键处理（翻页是宿主
    // 应用职责）——adapter 接 ArrowLeft/Right、PageUp/Down → 翻页；host 页
    // 与章节 iframe 两级都挂（系统焦点落在哪一级都能翻页）。
    const onKey = e => {
        const k = e.key
        if (k !== 'ArrowRight' && k !== 'ArrowLeft'
            && k !== 'PageDown' && k !== 'PageUp') return
        e.preventDefault()
        if (k === 'ArrowRight' || k === 'PageDown') view.renderer.next()
        else view.renderer.prev()
        say('keyboard turn: ' + k)
    }
    window.addEventListener('keydown', onKey)

    const onSectionMouseUp = async (index, doc) => {
        const sel = doc.getSelection()
        if (!sel || sel.isCollapsed || sel.rangeCount === 0) return
        const range = sel.getRangeAt(0)
        const quote = range.toString()
        if (!quote || quote.length < 2) return
        let cfi = ''
        try { cfi = view.getCFI(index, range) } catch (e) { cfi = '' }
        const { count } = await countOccurrences(book, quote)
        // occurrence：本选区在全书按 spine 序的出现位次。
        let occ = 1
        try {
            let before = 0
            for (let i = 0; i < index; i++) {
                const s = book.sections[i]
                if (!s || !s.createDocument) continue
                const d2 = await s.createDocument()
                const t2 = d2.body ? d2.body.textContent : ''
                let p = 0
                while (true) {
                    const at = t2.indexOf(quote, p)
                    if (at < 0) break
                    before++
                    p = at + 1
                }
            }
            const cur = doc.body ? doc.body.textContent : ''
            let p2 = 0
            while (true) {
                const at = cur.indexOf(quote, p2)
                if (at < 0) break
                before++
                p2 = at + 1
            }
            occ = before
        } catch (e) { occ = 1 }
        const msg = {
            schema_version: 1,
            kind: 'locator_select',
            session_id: sessionId,
            book_id: bookId,
            source_hash: sourceHash,
            engine: ENGINE_REVISION,
            resource_href: (book.sections[index] && book.sections[index].id) || ('section-' + index),
            resource_index: index,
            cfi: cfi,
            range_cfi: '',
            text_quote: quote,
            occurrence: occ,
            context_before: '',
            context_after: '',
            seq: (window.__reader.seq = (window.__reader.seq || 0) + 1),
            ts: Math.floor(Date.now() / 1000),
        }
        say('posting locator seq=' + msg.seq + ' occ=' + occ)
        const r = await fetch(locatorUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(msg),
        })
        const body = await r.text()
        window.__reader.events.push({ msg, resp: body })
        say('locator result: ' + body)
    }

    // 订阅去重：同一 section doc 只接一套 listener（load 重放/重排重建
    // 文档时重复接线会造成双 POST）。
    const subscribed = new WeakSet()

    const subscribeSection = (index, doc) => {
        if (!doc || subscribed.has(doc)) return
        subscribed.add(doc)
        // 键盘选择路径（Ctrl+A 真实输入时 selectionchange 触发回传）。
        doc.addEventListener('selectionchange', () => {
            const s = doc.getSelection()
            if (!s || s.isCollapsed || s.rangeCount === 0) return
            clearTimeout(doc.__selT)
            doc.__selT = setTimeout(() => { onSectionMouseUp(index, doc) }, 400)
        })
        doc.addEventListener('mouseup', () => { onSectionMouseUp(index, doc) })
        doc.addEventListener('keydown', onKey)
        // 输入可达性探针：真实指针按下经 fetch 回报（iframe 无 window.ipc，
        // 2026-11-02 实测 wry 仅主 frame 注入——HTTP 面让驱动可在消费日志验证）。
        doc.addEventListener('pointerdown', () => {
            fetch(locatorUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    schema_version: 1, kind: 'input_probe', session_id: sessionId,
                    book_id: bookId, source_hash: sourceHash, engine: ENGINE_REVISION,
                    resource_href: 'ping', resource_index: index, cfi: '', range_cfi: '',
                    text_quote: '', occurrence: 1, context_before: '', context_after: '',
                    seq: (window.__reader.ping = (window.__reader.ping || 0) + 1) + 100000,
                    ts: Math.floor(Date.now() / 1000),
                }),
            }).catch(() => {})
        })
    }

    view.addEventListener('load', ({ detail }) => {
        const { doc, index } = detail
        window.__reader.sectionIndex = index
        say('section loaded index=' + index)
        // 重排/翻页重建 section 文档时 load 重放——订阅经 WeakSet 去重后
        // 对新旧 doc 都成立。
        subscribeSection(index, doc)
    })

    // 已装载章节直接挂（init 期间 load 事件早于本订阅——订阅时序缺口）。
    for (const c of view.renderer.getContents()) {
        subscribeSection(c.index, c.doc)
    }

    // 状态面：引擎表面宿主的状态文本（无则静默——正式页由 .at 承载状态）。
    const status = document.querySelector('[data-reader-status]')
    if (status) {
        new MutationObserver(() => {}).observe(host, { childList: true })
        window.__reader.say = say
        say('adapter ready — engine ' + ENGINE_REVISION + ' loadMs=' + loadMs)
    }
    return { view, book, loadMs }
}
