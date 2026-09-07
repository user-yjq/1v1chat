import { expect, test } from '@playwright/test'

const username = `e2e_${Date.now()}`

test('注册 → 人设列表 → 进入会话 → 发送消息收到 AI 回复（前端冒烟）', async ({ page }) => {
  // 1) 注册并自动登录进入首页
  await page.goto('/register')
  await page.getByPlaceholder('3-64字符').fill(username)
  await page.getByPlaceholder('至少6位').fill('e2e-pass-2026')
  await page.getByRole('button', { name: '注册' }).click()
  await page.waitForURL('**/home')
  await expect(page.getByText('选一个“微信好友”开始聊天')).toBeVisible()

  // 2) seed 后应出现 4 个人设卡片，点“小雨”进入会话
  await expect(page.getByText('小雨', { exact: true }).first()).toBeVisible()
  await expect(page.getByText('桃桃', { exact: true }).first()).toBeVisible()
  await page.getByText('小雨', { exact: true }).first().click()
  await page.waitForURL(/\/chat\/\d+/)

  // 3) 发送一条消息，等用户气泡 + AI 气泡都出现（mock 引擎秒回）
  const input = page.getByPlaceholder(/输入消息/)
  await input.fill('哈喽，在吗？')
  await input.press('Enter')
  // 用户气泡 + AI 气泡都出现（引擎偶发一条回合双发，故用 ≥2）
  await expect.poll(() => page.locator('.msg-enter').count(), { timeout: 20_000 })
      .toBeGreaterThanOrEqual(2)
  await expect(page.getByText('哈喽，在吗？', { exact: true }).first()).toBeVisible()
})
