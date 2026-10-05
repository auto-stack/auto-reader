import { defineConfig, devices } from '@playwright/test'
// READER-001 T-09：chromium 可执行文件可经 PW_CHROMIUM 覆盖——本机
// ms-playwright 缓存缺 1.62.1 对应的 1234 号构建且 cdn.playwright.dev
// 不可达（实测两次下载中止），指向已有 1243 号全量 chrome 绕开 revision
// 门（UI 断言不依赖浏览器版本特性）。
const exe = process.env.PW_CHROMIUM
export default defineConfig({
  testDir: '.', testMatch: '*.spec.ts', fullyParallel: false,
  forbidOnly: !!process.env.CI, retries: process.env.CI ? 1 : 0, workers: 1,
  reporter: [['list'], ['html', { outputFolder: 'playwright-report', open: 'never' }]],
  outputDir: 'test-results/',
  use: {
    baseURL: process.env.BOOK_URL || 'http://localhost:17824',
    trace: 'on-first-retry', screenshot: 'only-on-failure', video: 'retain-on-failure',
    actionTimeout: 5000, navigationTimeout: 10000,
    ...(exe ? { launchOptions: { executablePath: exe } } : {}),
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
