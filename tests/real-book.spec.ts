/**
 * READER-001 Phase 3 UI 回归（T-11/T-14 / F-08/F-10/F-12）— 真实书阅读链路。
 * 前置：Vue 前端(17824) + VM 后端(17825) 以隔离 AUTO_READER_DATA 启动
 * （bash tests/spec/run_fresh_server.sh），本进程可见同一 AUTO_READER_DATA
 * （失效态注入直写 reading/<id>.json —— 后端 API 已拒绝非法状态，属预期）。
 * 覆盖：书架真实徽标 / 点段保存确认（内容锚点）/ 刷新恢复标记+提示 /
 *       恢复滚动（产品自滚，测试不代替滚动——reload 后直接断言视口交集）/
 *       显式章节不被旧状态覆盖 / 缺内容锚点与内容失配的诚实提示 /
 *       越界状态诚实提示 / emoji 段真实点击保存→恢复回环（F-10 Vue 面）。
 */
import { test, expect } from '@playwright/test'
import { spawnSync } from 'child_process'
import * as fs from 'fs'
import * as os from 'os'
import * as path from 'path'

const DATA = process.env.AUTO_READER_DATA || ''
const FIX = path.join(__dirname, 'fixtures', 'library')

function http(method: string, url: string, body?: unknown): any {
  // VM HTTP 层对 keep-alive 连接复用会劣化成空响应直至线程死亡（T-08 实测）
  // ——与 Python 驱动同款，用每请求新连接的 curl（spawnSync 数组参数，
  // 不经 shell）；空响应按竞态重试。
  for (let k = 0; k < 8; k++) {
    const args = ['-s', '-m', '20', '-X', method]
    let bodyFile: string | null = null
    if (body !== undefined) {
      // VM HTTP 层直连时按非 UTF-8 解码原始多字节请求体（T-00 登记缺陷；
      // 浏览器经 vite 代理不受影响）——直连客户端必须 ASCII 安全：
      // JSON.stringify 后把所有非 ASCII 字符转义（含代理对拆分）。
      const ascii = JSON.stringify(body).replace(/[\u0080-\uFFFF]/g, (ch) => {
        const cp = ch.codePointAt(0)!
        const h = cp.toString(16).padStart(4, '0')
        return cp > 0xffff
          ? '\u005cu' + h.slice(0, 4) + '\u005cu' + h.slice(4)
          : '\u005cu' + h
      })
      bodyFile = path.join(os.tmpdir(), `p3-body-${Date.now()}-${k}.json`)
      fs.writeFileSync(bodyFile, ascii, 'utf-8')
      args.push('-H', 'Content-Type: application/json', '-d', '@' + bodyFile)
    }
    args.push(url)
    const r = spawnSync('curl', args, { encoding: 'utf-8' })
    if (bodyFile) fs.unlinkSync(bodyFile)
    const out = r.stdout || ''
    if (out.trim()) {
      const v = JSON.parse(out)
      return typeof v === 'string' && v ? JSON.parse(v) : v
    }
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 300)
  }
  return { __empty__: true }
}

/** 生成一章多段的长文 fixture（恢复滚动需要目标段远离视口顶部）。 */
function makeLongBook(dir: string): string {
  const run = Date.now().toString(36)
  const p = path.join(dir, `ui-long-${run}.txt`)
  // 去重按内容判——每段注入运行标记，重跑不撞 duplicate
  const lines = [`第一章 长卷 ${run}`]
  for (let i = 1; i <= 60; i++) lines.push(`第${i}段的内容，山月不知心底事，水风空落眼前花。${run}`)
  fs.writeFileSync(p, lines.join('\n') + '\n', 'utf-8')
  return p
}

/** 生成含 emoji 与等长可替换段的 fixture（F-10/F-08 真实点击回环）。 */
function makeEmojiBook(dir: string): { path: string; run: string } {
  const run = Date.now().toString(36)
  const p = path.join(dir, `ui-emoji-${run}.txt`)
  const lines = [`第一章 表情 ${run}`, 'AAA' + run, 'A😀B' + run, '结尾' + run]
  fs.writeFileSync(p, lines.join('\n') + '\n', 'utf-8')
  return { path: p, run }
}

async function waitForShelf(page: import('@playwright/test').Page) {
  await page.goto('/')
  await page.locator('h1:has-text("Library")').waitFor({ timeout: 15000 })
  await page.waitForTimeout(800)
  // VM HTTP 空响应竞态（T-00 登记）：store 首拉可能得空书架——防御性
  // reload 一次（产品不重试是既有行为；测试自行恢复以隔离框架竞态）。
  if ((await page.locator('text=真实').count()) === 0) {
    await page.reload()
    await page.locator('h1:has-text("Library")').waitFor({ timeout: 15000 })
    await page.waitForTimeout(1200)
  }
}

test.describe('READER-001 真实书 UI', () => {
  let bookId = ''
  let longPath = ''
  let emojiId = ''
  let emojiPath = ''

  let emojiRun = ''
  test.beforeAll(() => {
    expect(DATA).toBeTruthy()
    longPath = makeLongBook(os.tmpdir())
    const emoji = makeEmojiBook(os.tmpdir())
    emojiPath = emoji.path
    emojiRun = emoji.run
    const o = http('POST', 'http://127.0.0.1:17825/api/library/import', { path: longPath, author: 'ui', force: false })
    expect(['ok', 'duplicate']).toContain(o.code)
    const listing = http('GET', 'http://127.0.0.1:17825/api/library/books')
    const mine = (listing.books as any[]).find((b) => b.title === path.basename(longPath, '.txt'))
    expect(mine).toBeTruthy()
    bookId = mine.book_id
    const o2 = http('POST', 'http://127.0.0.1:17825/api/library/import', { path: path.join(FIX, 'xiaoshuo.txt'), author: 'ui', force: false })
    expect(['ok', 'duplicate']).toContain(o2.code)
    const o3 = http('POST', 'http://127.0.0.1:17825/api/library/import', { path: emojiPath, author: 'ui', force: false })
    expect(['ok', 'duplicate']).toContain(o3.code)
    const listing3 = http('GET', 'http://127.0.0.1:17825/api/library/books')
    const mine3 = (listing3.books as any[]).find((b) => b.title === path.basename(emojiPath, '.txt'))
    expect(mine3).toBeTruthy()
    emojiId = mine3.book_id
  })

  test('T-R1: 书架展示真实书并带真实徽标', async ({ page }) => {
    await waitForShelf(page)
    await expect(page.locator('text=真实').first()).toBeVisible()
    await expect(page.locator('text=ui-long').first()).toBeVisible()
  })

  test('T-R2: 点段保存须后端确认后提示（F-05）', async ({ page }) => {
    await page.goto(`/#/book/${bookId}/chapter/1`)
    await page.locator('text=第3段的内容').waitFor({ timeout: 10000 })
    await page.locator('text=第3段的内容').click()
    await page.waitForTimeout(800)
    // ¶2 = 第3段（段序号 0 起，提示按 ¶ 序号显示）
    await expect(page.locator('text=已记录位置：第 2 段')).toBeVisible()
    // 服务端状态确实落盘（locator 校验通过后的确认语义）
    const st = http('GET', `http://127.0.0.1:17825/api/library/progress?book_id=${bookId}`)
    expect(st.paragraph_index).toBe(2)
    expect(st.chapter_number).toBe(1)
    // 内容锚点已注入存储态（F-08/F-10 的核对基础）
    expect(st.para_text).toContain('第3段的内容')
  })

  test('T-R3: 刷新后恢复标记+提示，产品自行滚入视口（F-12/F-05）', async ({ page }) => {
    // 保存第 56 段位置（body 行 55；API 语义等价于 UI 点段）
    const ch = http('GET', `http://127.0.0.1:17825/api/library/chapter?book_id=${bookId}&number=1`)
    const lines: string[] = ch.body.split('\n')
    const pi = 55
    const anchor = lines[pi].trim()
    const save = http('POST', 'http://127.0.0.1:17825/api/library/progress', {
      book_id: bookId,
      payload: JSON.stringify({ book_id: bookId, chapter_number: 1, paragraph_index: pi, para_hash: 'sig1:1:1', font_size: 'large', line_height: 'comfy', updated_at: 0 }),
      para_text: anchor,
    })
    console.log('T-R3 ANCHOR REPR:', JSON.stringify(anchor), 'len', anchor.length)
    console.log('T-R3 LINE55 REPR:', JSON.stringify(lines[55]), 'len', lines[55].length)
    console.log('T-R3 BODY-LINES:', lines.length, 'BODY-TAIL:', JSON.stringify(ch.body.slice(-80)))
    console.log('T-R3 SAVE RESPONSE:', JSON.stringify(save))
    expect(save.ok).toBe(true)
    await page.goto(`/#/book/${bookId}/chapter/1`)
    const marked = page.locator('.para-marked')
    await marked.waitFor({ timeout: 10000 })
    await expect(page.locator('text=已恢复上次位置（点任意段落可更新）')).toBeVisible()
    await expect(marked).toContainText('第56段的内容')
    // F-12：产品自行滚动——等待两段式恢复（溢出+精化）收敛后，不做任何
    // 测试侧滚动，直接断言标记段与视口相交。
    await expect
      .poll(
        async () => {
          const box = await marked.boundingBox()
          const vh = page.viewportSize()!.height
          const inView = !!box && box.y + box.height > 0 && box.y < vh
          const scrollState = await page.evaluate(() => {
            const el = document.querySelector('[data-scroll-ctl]') || document.querySelector('.overflow-y-auto, [class*=scroll]')
            const sc = el || document.scrollingElement
            return { top: sc ? (sc.scrollTop ?? 0) : -1, h: sc ? (sc.scrollHeight ?? 0) : -1, cls: el ? el.getAttribute('data-scroll-ctl') || el.className.slice(0, 60) : 'none' }
          })
          console.log('T-R3 poll:', JSON.stringify({ inView, y: box ? Math.round(box.y) : -1, vh, scroll: scrollState }))
          return inView
        },
        { timeout: 15000, intervals: [500, 1000, 2000] },
      )
      .toBe(true)
    // 精化完成后标记段应稳定可见（等待滚动动画/渲染稳定）
    await page.waitForTimeout(600)
    const box = await marked.boundingBox()
    const vh = page.viewportSize()!.height
    expect(box!.y + box!.height).toBeGreaterThan(0)
    expect(box!.y).toBeLessThan(vh)
    // 设置持久化（font_size=large 随状态恢复）
    const st2 = http('GET', `http://127.0.0.1:17825/api/library/progress?book_id=${bookId}`)
    expect(st2.font_size).toBe('large')
    expect(st2.paragraph_index).toBe(55)
  })

  test('T-R4: 显式打开第 2 章不被旧状态覆盖（F-05）', async ({ page }) => {
    // 多章书（xiaoshuo 3 章）；其保存状态在第 1 章，显式路由到第 2 章
    const listing2 = http('GET', 'http://127.0.0.1:17825/api/library/books')
    const xs = (listing2.books as any[]).find((b) => b.title === 'xiaoshuo')
    expect(xs).toBeTruthy()
    const ch2 = http('GET', `http://127.0.0.1:17825/api/library/chapter?book_id=${xs.book_id}&number=2`)
    expect(String(ch2.title)).not.toBe('章节不存在')
    await page.goto(`/#/book/${xs.book_id}/chapter/2`)
    await page.waitForTimeout(1200)
    expect(page.url()).toContain('/chapter/2')
    await expect(page.locator('text=Chapter 2 of')).toBeVisible()
    await expect(page.locator('text=已恢复上次位置')).toHaveCount(0)
  })

  test('T-R5: 缺内容锚点的旧状态诚实提示（F-08）', async ({ page }) => {
    // 直写状态文件模拟 Phase 2 旧态（sig1-only、无 para_text）
    const rp = path.join(DATA, 'reading', `${bookId}.json`)
    const legacy = { book_id: bookId, chapter_number: 1, paragraph_index: 3, para_hash: 'sig1:5:1', font_size: 'medium', line_height: 'comfy', updated_at: 0 }
    fs.writeFileSync(rp, JSON.stringify(legacy), 'utf-8')
    await page.goto(`/#/book/${bookId}/chapter/1`)
    await expect(page.locator('text=上次保存的位置缺少内容锚点，请重新点选段落')).toBeVisible({ timeout: 10000 })
    await expect(page.locator('text=已恢复上次位置')).toHaveCount(0)
    await expect(page.locator('.para-marked')).toHaveCount(0)
  })

  test('T-R5b: 内容失配状态诚实提示（F-08）', async ({ page }) => {
    // 内容锚点在场但与当前原文不符（源已变化/等长替换语义）
    const rp = path.join(DATA, 'reading', `${bookId}.json`)
    const mismatch = { book_id: bookId, chapter_number: 1, paragraph_index: 3, para_hash: 'sig1:5:1', para_text: '完全不同的历史内容', font_size: 'medium', line_height: 'comfy', updated_at: 0 }
    fs.writeFileSync(rp, JSON.stringify(mismatch), 'utf-8')
    await page.goto(`/#/book/${bookId}/chapter/1`)
    await expect(page.locator('text=上次保存的段落内容已变化，请重新点选位置')).toBeVisible({ timeout: 10000 })
    await expect(page.locator('text=已恢复上次位置')).toHaveCount(0)
    await expect(page.locator('.para-marked')).toHaveCount(0)
  })

  test('T-R6: 越界段落状态诚实提示（F-05）', async ({ page }) => {
    const rp = path.join(DATA, 'reading', `${bookId}.json`)
    const stale = { book_id: bookId, chapter_number: 1, paragraph_index: 999, para_hash: 'sig1:999:1', font_size: 'medium', line_height: 'comfy', updated_at: 0 }
    fs.writeFileSync(rp, JSON.stringify(stale), 'utf-8')
    await page.goto(`/#/book/${bookId}/chapter/1`)
    await expect(page.locator('text=上次保存的段落在本章已不存在，请重新点选位置')).toBeVisible({ timeout: 10000 })
    await expect(page.locator('.para-marked')).toHaveCount(0)
  })

  test('T-R7: xiaoshuo 真实书章节逐字渲染', async ({ page }) => {
    const books = http('GET', 'http://127.0.0.1:17825/api/library/books')
    const x = (books.books as any[]).find((b) => b.title === 'xiaoshuo')
    expect(x).toBeTruthy()
    await page.goto(`/#/book/${x.book_id}/chapter/1`)
    await expect(page.locator('text=山月不知心底事，水风空落眼前花。')).toBeVisible({ timeout: 10000 })
    await expect(page.locator('text=第一章 山月').first()).toBeVisible()
  })

  test('T-R8: emoji 段真实点击保存→刷新恢复回环（F-10 Vue 面）', async ({ page }) => {
    await page.goto(`/#/book/${emojiId}/chapter/1`)
    const emojiPara = page.locator('text=A😀B').first()
    await emojiPara.waitFor({ timeout: 10000 })
    await emojiPara.click()
    await page.waitForTimeout(800)
    await expect(page.locator('text=已记录位置：第 1 段')).toBeVisible()
    // 刷新后按内容锚点恢复（emoji 全链路：保存→存储→恢复核对）
    await page.reload()
    const marked = page.locator('.para-marked')
    await marked.waitFor({ timeout: 10000 })
    await expect(page.locator('text=已恢复上次位置（点任意段落可更新）')).toBeVisible()
    await expect(marked).toContainText('A😀B')
    const st = http('GET', `http://127.0.0.1:17825/api/library/progress?book_id=${emojiId}`)
    expect(st.para_text).toBe('A😀B' + emojiRun)
  })
})
