/**
 * READER-001 Phase 2 UI 回归（T-08 / F-05）— 真实书阅读链路。
 * 前置：Vue 前端(17824) + VM 后端(17825) 以隔离 AUTO_READER_DATA 启动
 * （bash tests/spec/run_fresh_server.sh），本进程可见同一 AUTO_READER_DATA
 * （失效态注入直写 reading/<id>.json —— 后端 API 已拒绝非法状态，属预期）。
 * 覆盖：书架真实徽标 / 段落逐字 / 点段保存确认 / 刷新恢复标记+提示 /
 *       显式章节不被旧状态覆盖 / 锚点失配诚实提示 / 越界状态诚实提示 /
 *       字号随状态恢复（滚动位置恢复为登记的框架能力差距，见计划 §10）。
 */
import { test, expect } from '@playwright/test'
import { spawnSync } from 'child_process'
import * as fs from 'fs'
import * as os from 'os'
import * as path from 'path'

const DATA = process.env.AUTO_READER_DATA || ''
const FIX = path.join(__dirname, 'fixtures', 'library')

function http(method: string, url: string, body?: unknown): any {
  // VM HTTP 层对 keep-alive 连接复用会劣化成空响应直至线程死亡（T-08 实测：
  // node fetch 连发数请求后全部 0ms 空响应体）——与 Python 驱动同款，用
  // 每请求新连接的 curl（spawnSync 数组参数，不经 shell，JSON 体无引号问题）；
  // 空响应按 T-00 §13 竞态重试。
  for (let k = 0; k < 3; k++) {
    const args = ['-s', '-m', '20', '-X', method]
    if (body !== undefined) {
      args.push('-H', 'Content-Type: application/json', '-d', JSON.stringify(body))
    }
    args.push(url)
    const r = spawnSync('curl', args, { encoding: 'utf-8' })
    const out = r.stdout || ''
    if (out.trim()) {
      const v = JSON.parse(out)
      return typeof v === 'string' && v ? JSON.parse(v) : v
    }
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 300)
  }
  return { __empty__: true }
}

/** 生成一章多段的长文 fixture（标记段远离视口顶部；内容级运行唯一）。 */
function makeLongBook(dir: string): string {
  const run = Date.now().toString(36)
  const p = path.join(dir, `ui-long-${run}.txt`)
  // 去重按内容判——每段注入运行标记，重跑不撞 duplicate
  const lines = [`第一章 长卷 ${run}`]
  for (let i = 1; i <= 60; i++) lines.push(`第${i}段的内容，山月不知心底事，水风空落眼前花。${run}`)
  fs.writeFileSync(p, lines.join('\n') + '\n', 'utf-8')
  return p
}

async function waitForShelf(page: import('@playwright/test').Page) {
  await page.goto('/')
  await page.locator('h1:has-text("Library")').waitFor({ timeout: 15000 })
  await page.waitForTimeout(800)
}

test.describe('READER-001 真实书 UI', () => {
  let bookId = ''
  let longPath = ''

  test.beforeAll(() => {
    expect(DATA).toBeTruthy()
    longPath = makeLongBook(os.tmpdir())
    const o = http('POST', 'http://127.0.0.1:17825/api/library/import', { path: longPath, author: 'ui', force: false })
    expect(['ok', 'duplicate']).toContain(o.code)
    // 标题解析兜底（重跑时 duplicate → 取既有书目 id）
    const listing = http('GET', 'http://127.0.0.1:17825/api/library/books')
    const mine = (listing.books as any[]).find((b) => b.title === path.basename(longPath, '.txt'))
    expect(mine).toBeTruthy()
    bookId = mine.book_id
    const o2 = http('POST', 'http://127.0.0.1:17825/api/library/import', { path: path.join(FIX, 'xiaoshuo.txt'), author: 'ui', force: false })
    expect(['ok', 'duplicate']).toContain(o2.code)
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
  })

  test('T-R3: 刷新后恢复标记与提示（F-05）', async ({ page }) => {
    // 保存第 55 段位置（经 UI 语义等价的 API，锚点合法）
    const st = http('GET', `http://127.0.0.1:17825/api/library/progress?book_id=${bookId}`)
    const ch = http('GET', `http://127.0.0.1:17825/api/library/chapter?book_id=${bookId}&number=1`)
    const lines: string[] = ch.body.split('\n')
    const pi = 55 // body 行 55 = 第56段（0 起；恢复标记即应落在 ¶55）
    const sig = `sig1:${lines[pi].trim().length}:1`
    const save = http('POST', 'http://127.0.0.1:17825/api/library/progress', {
      book_id: bookId,
      payload: JSON.stringify({ book_id: bookId, chapter_number: 1, paragraph_index: pi, para_hash: sig, font_size: 'large', line_height: 'comfy', updated_at: 0 }),
    })
    expect(save.ok).toBe(true)
    await page.goto(`/#/book/${bookId}/chapter/1`)
    const marked = page.locator('.para-marked')
    await marked.waitFor({ timeout: 10000 })
    await expect(page.locator('text=已恢复上次位置（点任意段落可更新）')).toBeVisible()
    // 标记落在保存的那一段（内容级恢复证据；滚动位置恢复为登记的框架差距）
    await marked.scrollIntoViewIfNeeded()
    await expect(marked).toContainText('第56段的内容')
    // 字号随状态恢复（设置持久化由 t02 HTTP 逐字证明；阅读页排版应用为
    // Phase-1 T-03 既有行为）——此处断言恢复来源状态正确
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

  test('T-R5: 锚点失配状态诚实提示需重定位（F-05）', async ({ page }) => {
    // 直接写状态文件构造"源已变化"的失配态（后端 API 按设计拒绝失配锚点）
    const rp = path.join(DATA, 'reading', `${bookId}.json`)
    const stale = { book_id: bookId, chapter_number: 1, paragraph_index: 3, para_hash: 'sig1:999:1', font_size: 'medium', line_height: 'comfy', updated_at: 0 }
    fs.writeFileSync(rp, JSON.stringify(stale), 'utf-8')
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
})
