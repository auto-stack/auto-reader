/**
 * auto-os/PLAN-059 theme-adoption counter-controls（V-01/V-03 产品腿；vue 轨）。
 * 前置：Vue 前端(17824) + VM 后端(17825) 以隔离 AUTO_READER_DATA + 腿环境
 * （AUTO_UI_THEME / AUTOOS_DESKTOP_CONFIG）启动（test_059_theme.py 生命周期
 * 管理），product-alpha 语料已由 runner 预导入。
 *
 * oracle 纪律：壳色 = 应用壳根元素 computed backgroundColor 与官方包 token
 * 精确相等（非仅类名）；引擎色 = doc-surface 内 foliate 文档 html 背景
 * computed 值精确相等；引擎主题读回 = window.__reader.appliedSettings.theme
 * （READER-007 命令端口消费证明）。真实书卡可见 = 业务哨兵（V-02 换肤不丢
 * 书库数据）。截图证据落 T59_ART。
 */
import { test, expect } from '@playwright/test'
import * as fs from 'fs'
import * as path from 'path'

const SHELL_RGB = process.env.T59_SHELL_RGB || ''
const READ_THEME = process.env.T59_READ_THEME || ''
const ENGINE_RGB = process.env.T59_ENGINE_RGB || ''
const BOOK_TITLE = process.env.T59_BOOK || '山月与潮声'
const APPLY_SEPIA = process.env.T59_APPLY_SEPIA === '1'
const ART = process.env.T59_ART || ''

/** 面积最大的命中元素（壳根 bg-background 行；避免多命中次序脆弱）。 */
async function shellBg(page: import('@playwright/test').Page): Promise<string | null> {
  return page.evaluate(() => {
    let best: Element | null = null
    let area = 0
    for (const el of Array.from(document.querySelectorAll('.bg-background'))) {
      const r = el.getBoundingClientRect()
      const a = r.width * r.height
      if (a > area) {
        area = a
        best = el
      }
    }
    return best ? getComputedStyle(best).backgroundColor : null
  })
}

test('PLAN-059 shelf: shell token + real book sentinel', async ({ page }) => {
  test.setTimeout(120_000)
  // 冷 gen 全量按需编译时首载远超 10s 默认导航门
  page.setDefaultNavigationTimeout(120_000)
  await page.goto('/#/')
  // 业务哨兵：真实语料书卡在书架可见（导入由 runner 经 /api/library/import 完成）
  await expect(page.getByText(BOOK_TITLE).first()).toBeVisible({ timeout: 90_000 })
  const bg = await shellBg(page)
  expect(bg, 'shell root computed background').toBe(SHELL_RGB)
  if (ART) {
    fs.mkdirSync(ART, { recursive: true })
    await page.screenshot({ path: path.join(ART, `shelf-${READ_THEME || 'default'}.png`), fullPage: false })
  }
})

test('PLAN-059 reading: engine port readback + engine color', async ({ page }) => {
  test.setTimeout(180_000)
  page.setDefaultNavigationTimeout(120_000)
  // 由后端 API 定位语料书 id（不猜路由参数；.at 后端可能双层 JSON 编码）
  const resp = await page.request.get('http://127.0.0.1:17825/api/library/books')
  let lib: any = await resp.json()
  if (typeof lib === 'string' && lib) lib = JSON.parse(lib)
  let bid = ''
  for (const b of lib.books || []) {
    if (b.title === BOOK_TITLE) bid = String(b.book_id)
  }
  expect(bid, 'corpus book imported').not.toBe('')
  await page.goto(`/#/book/${bid}/chapter/1`)
  // adapter 就绪（READER-007 产品装载链：doc-surface 宿主 + mountProbe）
  await page.waitForFunction(() => !!(window as any).__reader, { timeout: 90_000 })
  // 等命令队列消费（Init 末段 settings 已入队；appliedSettings 出现即回执）
  await page.waitForFunction(() => {
    const s = (window as any).__reader?.appliedSettings
    return !!s && typeof s === 'object'
  }, { timeout: 90_000 })
  if (APPLY_SEPIA) {
    // 显式主题腿：打开排版抽屉（Aa）点「米」= sepia（真实用户路径；real book 持久化）
    const aa = page.getByText('Aa', { exact: true }).first()
    await expect(aa).toBeVisible({ timeout: 30_000 })
    await aa.click()
    const sepiaBtn = page.getByText('米', { exact: true }).first()
    await expect(sepiaBtn).toBeVisible({ timeout: 30_000 })
    await sepiaBtn.click()
    await page.waitForFunction(() => (window as any).__reader?.appliedSettings?.theme === 'sepia', { timeout: 30_000 })
  }
  const applied = await page.evaluate(() => (window as any).__reader?.appliedSettings?.theme ?? null)
  expect(applied, 'engine port theme readback').toBe(READ_THEME)
  if (ENGINE_RGB) {
    const engineBg = await page.waitForFunction(() => {
      // foliate-view → foliate-paginator 双层 shadow root 内才是引擎文档
      // iframe（shadow 边界不透 querySelectorAll——必须递归下钻）。
      const seen: ShadowRoot[] = []
      const collectFrames = (root: Document | ShadowRoot, out: HTMLIFrameElement[]) => {
        for (const f of Array.from(root.querySelectorAll('iframe'))) {
          out.push(f as HTMLIFrameElement)
        }
        for (const el of Array.from(root.querySelectorAll('*'))) {
          const sr = (el as any).shadowRoot as ShadowRoot | null
          if (sr && !seen.includes(sr)) {
            seen.push(sr)
            collectFrames(sr, out)
          }
        }
      }
      const frames: HTMLIFrameElement[] = []
      collectFrames(document, frames)
      for (const f of frames) {
        try {
          const d = f.contentDocument
          const win = d?.defaultView
          if (!d || !win) continue
          const bg = win.getComputedStyle(d.documentElement).backgroundColor
          if (bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent') return bg
        } catch {
          // 跨域 frame：跳过
        }
      }
      return null
    }, null, { timeout: 90_000, polling: 500 })
    expect((await engineBg.jsonValue()) as string, 'engine document html background').toBe(ENGINE_RGB)
  }
  if (ART) {
    fs.mkdirSync(ART, { recursive: true })
    await page.screenshot({ path: path.join(ART, `reading-${applied}.png`), fullPage: false })
  }
})
