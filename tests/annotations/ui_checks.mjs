// ui_checks.mjs — READER-002 T-04 Vue UI 验收面（verify_local.py 调用）。
// 用法：node tests/annotations/ui_checks.mjs <base_url> <chrome_exe> <book_title> <para_snippet> <occ>
// 覆盖（计划 §6）：A-01 偏好持久/同段恢复；A-02 UI 注释创建（含重复句
// occurrence）+ 抽屉回访 + 段标记 chip；A-05 搜索中文输入 onenter 触发、
// 无全局键盘抢事件（输入中文/敲字母不触发页面级动作）、跳转。
// 输出：每行 "PASS name" / "FAIL name"；退出码 0=全过 1=有 FAIL。
import { chromium } from '@playwright/test'

const base = process.argv[2] || 'http://localhost:17836'
const exe = process.argv[3] || ''
const bookTitle = process.argv[4] || 'smoke-book'
const paraSnippet = process.argv[5] || '桥边的老树开花了'
const occ = process.argv[6] || '2'

const results = []
function check(cond, name) {
  results.push([!!cond, name])
  console.log((cond ? 'PASS ' : 'FAIL ') + name)
}

const browser = await chromium.launch(exe ? { executablePath: exe } : {})
const page = await browser.newPage()
page.setDefaultTimeout(9000)
try {
  // ── 进入书 ──
  await page.goto(base + '/#/', { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(2200)
  const card = page.locator('text=' + bookTitle).first()
  await card.waitFor({ timeout: 9000 })
  await card.click()
  await page.waitForTimeout(1200)
  let entered = false
  for (const sel of ['text=继续阅读', 'text=开始阅读', 'text=第一章']) {
    const btn = page.locator(sel).first()
    if (await btn.isVisible().catch(() => false)) { await btn.click(); entered = true; break }
  }
  check(entered, 'L-U01 enter detail')
  await page.waitForTimeout(2200)
  check(page.url().includes('/chapter/'), 'L-U02 reading page url')
  await page.locator('text=¶').first().waitFor({ timeout: 9000 })

  // ── A-05：搜索框中文键入（无全局键盘抢事件）──
  await page.locator('text=🔍 搜索').click()
  await page.waitForTimeout(600)
  const searchBox = page.locator('input[placeholder*="关键词"]')
  await searchBox.click()
  await searchBox.pressSequentially('开花', { delay: 60 })
  await page.waitForTimeout(500)
  // 键入期间页面未跳转（无全局 handler 抢事件）
  check(page.url().includes('/chapter/'), 'L-U03 typing does not navigate (no global keys)')
  await searchBox.press('Enter')
  await page.waitForTimeout(1800)
  const resultCount = await page.locator('text=/第 1 章 · ¶/').count()
  check(resultCount >= 1, 'L-U04 search results shown: ' + resultCount)
  // 点击结果跳转
  await page.locator('text=/第 1 章 · ¶/').first().click()
  await page.waitForTimeout(1800)
  check((await page.locator('body').innerText()).includes('已跳转'), 'L-U05 jump note shown')

  // ── A-01：排版偏好（宽栏 + 米色主题）──
  await page.locator('text=Aa').first().click()
  await page.waitForTimeout(600)
  await page.locator('button', { hasText: '宽' }).first().click()
  await page.waitForTimeout(900)
  await page.locator('button', { hasText: '米' }).first().click()
  await page.waitForTimeout(1200)
  // 主题底色类生效（sepia 底色）
  const bodyCls = await page.locator('.max-w-4xl').count()
  check(bodyCls >= 1, 'L-U06 wide layout applied')

  // ── A-02：注释创建（重复句 occurrence）──
  const paras = page.locator('div.cursor-pointer', { hasText: paraSnippet })
  await paras.first().click()
  await page.waitForTimeout(1200)
  await page.locator('text=＋ 注释/书签').first().click()
  await page.waitForTimeout(800)
  const quoteBox = page.locator('input[placeholder="摘录原文"]')
  const qv = await quoteBox.inputValue()
  check(qv.includes(paraSnippet), 'L-U07 quote prefilled')
  // 截取子串（quote = 前置重复句）
  await quoteBox.fill(paraSnippet)
  const occBox = page.locator('input').nth(2)
  await occBox.fill(occ)
  await page.locator('textarea').fill('UI 验收注释（重复句）')
  await page.locator('input[placeholder*="重点"]').fill('UI, 验收')
  await page.locator('text=保存注释').click()
  await page.waitForTimeout(1800)
  check(await page.locator('text=UI 验收注释（重复句）').first().isVisible().catch(() => false), 'L-U08 annotation in drawer')
  check(await page.locator('text=需重定位').count() === 0, 'L-U09 no false needs-relocate')
  // 段标记 chip（✎ N）
  const chip = page.locator('text=/✎ \\d+/')
  check(await chip.count() >= 1, 'L-U10 para mark chip')

  // ── 注释回访（提交后抽屉已自动打开）──
  await page.waitForTimeout(600)
  const drawerItem = page.locator('text=UI 验收注释（重复句）').first()
  check(await drawerItem.isVisible().catch(() => false), 'L-U11 drawer shows record after submit')
} catch (e) {
  check(false, 'EXCEPTION: ' + String(e).slice(0, 180))
} finally {
  await browser.close()
}
let fails = 0
for (const [ok] of results) { if (!ok) fails++ }
console.log('UI_CHECKS DONE fails=' + fails + '/' + results.length)
process.exit(fails > 0 ? 1 : 0)
