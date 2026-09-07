import { expect, test } from '@playwright/test'

const username = `e2e_${Date.now()}`

async function dumpDiagnostics(page: import('@playwright/test').Page, label: string) {
  console.log(`[diag:${label}] url=${page.url()}`)
  const text = await page.locator('body').innerText().catch(() => '(no body)')
  console.log(`[diag:${label}] body=${text.slice(0, 400).replace(/\n+/g, ' | ')}`)
}

test('注册 → 人设列表 → 进入会话 → 发送消息收到 AI 回复（前端冒烟）', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`))
  page.on('console', (m) => {
    if (m.type() === 'error') errors.push(`console: ${m.text()}`)
  })

  // 1) 注册并自动登录进入首页
  await page.goto('/register', { waitUntil: 'domcontentloaded' })
  try {
    await page.getByRole('heading', { name: '注册' }).waitFor({ timeout: 15_000 })
  } catch {
    await dumpDiagnostics(page, 'register-heading')
    throw new Error('注册页未出现标题（可能被路由弹回登录/白屏）')
  }
  await page.getByPlaceholder('3-64字符').fill(username)
  await page.getByPlaceholder('至少6位').fill('e2e-pass-2026')
  await page.getByRole('button', { name: '注册' }).click()
  try {
    await page.waitForURL('**/home', { timeout: 15_000 })
  } catch {
    await dumpDiagnostics(page, 'after-register')
    throw new Error(`注册后未进入 /home；errors=${errors.join(' || ')}`)
  }
  await expect(page.getByText('选一个“微信好友”开始聊天')).toBeVisible()

  // 2) seed 后应出现人设卡片，点“小雨”进入会话
  await expect(page.getByText('小雨', { exact: true }).first()).toBeVisible()
  await page.getByText('小雨', { exact: true }).first().click()
  await page.waitForURL(/\/chat\/\d+/)

  // 3) 发送一条消息，等用户气泡 + AI 气泡都出现（引擎偶发双发，用 ≥2）
  const input = page.getByPlaceholder(/输入消息/)
  await input.fill('哈喽，在吗？')
  await input.press('Enter')
  await expect.poll(() => page.locator('.msg-enter').count(), { timeout: 25_000 })
      .toBeGreaterThanOrEqual(2)
  await expect(page.getByText('哈喽，在吗？', { exact: true }).first()).toBeVisible()
  expect(errors).toEqual([])
})
