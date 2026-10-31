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

test('R-02 真实图像渲染：解码成功、身份互异、错误诚实可见', async ({ page }) => {
  test.setTimeout(60_000)
  const bid = bookIdByTitle('Probe Book 2')
  expect(bid, '夹具书 Probe Book 2 应已预导入').toBeTruthy()
  await page.goto(`http://localhost:17824/#/book/${bid}/chapter/1`)
  await expect(page.locator('h1').first()).toContainText('C1', { timeout: 20_000 })

  // 三个合法图像（两扁平碰撞 + 一含空格名）全部真实解码
  const imgs = page.locator('img[src*="/api/reader/media/"]')
  await expect(imgs).toHaveCount(3, { timeout: 20_000 })
  const srcs: string[] = []
  for (let i = 0; i < 3; i++) {
    const src = await imgs.nth(i).getAttribute('src')
    srcs.push(String(src))
    const nw = await imgs.nth(i).evaluate((el: HTMLImageElement) => el.naturalWidth)
    expect(nw, `图像 ${i} 必须真实解码（naturalWidth>0）`).toBeGreaterThan(0)
  }
  // 双射扁平名 → 三 src 互异（同槽错图在此显形）
  expect(new Set(srcs).size, '三张图 src 必须互异').toBe(3)

  // 不支持形态：诚实错误行 + 拒绝码可见，不静默消失
  await expect(page.getByText('⚠ 插图不可用')).toHaveCount(1)
  await expect(page.getByText('img_unsupported_type')).toHaveCount(1)

  // 再开同章（前端重载同一路由）— URI 稳定
  await page.reload()
  await expect(page.locator('img[src*="/api/reader/media/"]')).toHaveCount(3, { timeout: 20_000 })
  for (let i = 0; i < 3; i++) {
    const nw = await page.locator('img[src*="/api/reader/media/"]').nth(i).evaluate((el: HTMLImageElement) => el.naturalWidth)
    expect(nw).toBeGreaterThan(0)
  }
})
