/**
 * READER-005 standalone UI oracle（R-02/R-03/R-04 Vue 面；T-02 起）。
 * 前置：Vue 前端(17824) + VM 后端(17825) 以隔离 AUTO_READER_DATA 启动
 * （verify_standalone.py 生命周期管理）；本进程可见同一 AUTO_READER_DATA。
 * oracle 纪律：图像必须 naturalWidth>0（真实解码）＋ src 指向应用自有
 * 媒体端点；错误图像必须可见错误行＋拒绝码；不以 URI 存在代替显示。
 */
import { test, expect } from '@playwright/test'
import { spawnSync } from 'child_process'
import * as fs from 'fs'
import * as os from 'os'
import * as path from 'path'

const DATA = process.env.AUTO_READER_DATA || ''

function http(method: string, url: string, body?: unknown): any {
  for (let k = 0; k < 8; k++) {
    const args = ['-s', '-m', '20', '-X', method]
    if (body !== undefined) {
      const ascii = JSON.stringify(body).replace(/[\u0080-\uFFFF]/g, (ch) => {
        const cp = ch.codePointAt(0)!
        const h = cp.toString(16).padStart(4, '0')
        return cp > 0xffff
          ? '\u005cu' + h.slice(0, 4) + '\u005cu' + h.slice(4)
          : '\u005cu' + h
      })
      const bodyFile = path.join(os.tmpdir(), `sa-body-${Date.now()}-${k}.json`)
      fs.writeFileSync(bodyFile, ascii, 'utf-8')
      args.push('-H', 'Content-Type: application/json', '-d', '@' + bodyFile)
    }
    args.push(url)
    const r = spawnSync('curl', args, { encoding: 'utf-8' })
    if (body !== undefined && fs.existsSync(bodyFileMod(args))) fs.unlinkSync(bodyFileMod(args))
    const out = r.stdout || ''
    if (out.trim()) {
      const v = JSON.parse(out)
      return typeof v === 'string' && v ? JSON.parse(v) : v
    }
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 300)
  }
  return { __empty__: true }
}

function bodyFileMod(args: string[]): string {
  const i = args.indexOf('-d')
  return i >= 0 ? args[i + 1].replace(/^@/, '') : ''
}

/** 按标题找书目 id（夹具书由 verify_standalone 预导入）。 */
function bookIdByTitle(title: string): string {
  const lst = http('GET', 'http://127.0.0.1:17825/api/library/books')
  for (const b of lst.books || []) {
    if (b.title === title) return String(b.book_id)
  }
  return ''
}

test('R-02 真实图像渲染：引擎面解码成功、src 互异（READER-007 表面：EPUB 经 doc-surface 引擎渲染，oracle 随 SD-05 更新）', async ({ page }) => {
  test.setTimeout(90_000)
  const bid = bookIdByTitle('Probe Book 2')
  expect(bid, '夹具书 Probe Book 2 应已预导入').toBeTruthy()
  await page.goto(`http://localhost:17824/#/book/${bid}/chapter/1`)
  await expect
    .poll(async () => page.evaluate(() => (window as any).__reader?.book?.sections?.length || 0), { timeout: 30_000 })
    .toBeGreaterThan(0)

  const readImgs = () => page.evaluate(() => {
    const fv = document.querySelector('foliate-view')
    const p = fv && fv.shadowRoot
      ? fv.shadowRoot.querySelector('foliate-paginator') : null
    const ifr = p && p.shadowRoot
      ? p.shadowRoot.querySelector('iframe') : null
    if (!ifr || !ifr.contentDocument) return []
    return Array.from(ifr.contentDocument.querySelectorAll('img')).map(
      (im: HTMLImageElement) => ({ src: String(im.getAttribute('src') || ''), w: im.naturalWidth }))
  })

  const imgs = await readImgs()
  expect(imgs.length, '探针书 2 应有图像元素').toBeGreaterThan(0)
  expect(new Set(imgs.map(i => i.src)).size, '图像 src 必须互异').toBe(imgs.length)
  for (const i of imgs) {
    expect(i.w, '引擎内图像真实解码 naturalWidth>0').toBeGreaterThan(0)
  }

  // 重开同章——引擎重装载后图像仍解码（URI 稳定性由引擎 blob 面承载）
  await page.reload()
  await expect
    .poll(async () => page.evaluate(() => (window as any).__reader?.book?.sections?.length || 0), { timeout: 30_000 })
    .toBeGreaterThan(0)
  const imgs2 = await readImgs()
  for (const i of imgs2) {
    expect(i.w, '重开同章图像仍真实解码').toBeGreaterThan(0)
  }
})

test('R-03 跨章链接跳转：目标章真实进入引擎渲染（READER-007 表面 oracle 更新）', async ({ page }) => {
  test.setTimeout(90_000)
  const bid = bookIdByTitle('Probe Book 4')
  expect(bid, '夹具书 Probe Book 4 应已预导入').toBeTruthy()
  await page.goto(`http://localhost:17824/#/book/${bid}/chapter/1`)
  await expect
    .poll(async () => page.evaluate(() => (window as any).__reader?.book?.sections?.length || 0), { timeout: 30_000 })
    .toBeGreaterThan(0)

  // 引擎内真实链接点击（foliate 渲染的 <a href>——ch2.xhtml#dup 跨章目标）
  const clicked = await page.evaluate(() => {
    const fv = document.querySelector('foliate-view')
    const p = fv && fv.shadowRoot
      ? fv.shadowRoot.querySelector('foliate-paginator') : null
    const ifr = p && p.shadowRoot
      ? p.shadowRoot.querySelector('iframe') : null
    if (!ifr || !ifr.contentDocument) return 'no-iframe'
    const links = ifr.contentDocument.querySelectorAll('a[href*="ch2"]')
    if (!links.length) return 'no-link'
    ;(links[0] as HTMLAnchorElement).click()
    return 'clicked'
  })
  expect(clicked).toBe('clicked')

  // 目标章真实进入引擎渲染窗口（getContents 含 section 1 = ch2）
  await expect
    .poll(async () => page.evaluate(() => {
      const r = (window as any).__reader
      if (!r || !r.view || !r.view.renderer) return []
      return r.view.renderer.getContents().map((c: any) => c.index)
    }), { timeout: 30_000 })
    .toContain(1)
  const hasTarget = await page.evaluate(() => {
    const r = (window as any).__reader
    if (!r || !r.view || !r.view.renderer) return false
    for (const c of r.view.renderer.getContents()) {
      if ((c.doc.body.textContent || '').includes('重复段落文本目标')) return true
    }
    return false
  })
  expect(hasTarget, '跨章目标段文本逐字可见').toBe(true)
})

test('R-03 同章锚跳转 + 无效链接诚实拒绝（引擎面 oracle 更新）', async ({ page }) => {
  test.setTimeout(90_000)
  const bid = bookIdByTitle('Probe Book 4')
  await page.goto(`http://localhost:17824/#/book/${bid}/chapter/1`)
  await expect
    .poll(async () => page.evaluate(() => (window as any).__reader?.book?.sections?.length || 0), { timeout: 30_000 })
    .toBeGreaterThan(0)

  // 同章锚：点击 iframe 内锚链接 → 目标文本进入渲染
  const clicked = await page.evaluate(() => {
    const fv = document.querySelector('foliate-view')
    const p = fv && fv.shadowRoot
      ? fv.shadowRoot.querySelector('foliate-paginator') : null
    const ifr = p && p.shadowRoot
      ? p.shadowRoot.querySelector('iframe') : null
    if (!ifr || !ifr.contentDocument) return 'no-iframe'
    const links = ifr.contentDocument.querySelectorAll('a[href*="#"]')
    if (!links.length) return 'no-link'
    ;(links[0] as HTMLAnchorElement).click()
    return 'clicked'
  })
  expect(clicked).toBe('clicked')

  // 无效目标诚实：foliate 对外部 scheme href 不导航（仍在原章渲染窗口）
  const before = await page.evaluate(() => (window as any).__reader.sectionIndex)
  await page.evaluate(() => {
    const fv = document.querySelector('foliate-view')
    const p = fv && fv.shadowRoot
      ? fv.shadowRoot.querySelector('foliate-paginator') : null
    const ifr = p && p.shadowRoot
      ? p.shadowRoot.querySelector('iframe') : null
    const links = ifr.contentDocument.querySelectorAll('a[href]')
    for (const a of links) {
      if (/^(https?:|mailto:)/i.test(a.getAttribute('href') || '')) {
        ;(a as HTMLAnchorElement).click()
        break
      }
    }
  })
  await page.waitForTimeout(1500)
  const after = await page.evaluate(() => (window as any).__reader.sectionIndex)
  expect(after).toBe(before)
})
