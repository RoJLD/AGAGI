import { test, expect } from '@playwright/test';

const FRONTEND = process.env.FRONTEND_URL || 'http://localhost:4173';
const API = process.env.API_URL || 'http://localhost:8001';

test('loads dashboard and academy content', async ({ page }) => {
  await page.goto(FRONTEND);
  await expect(page.locator('h1')).toHaveText(/AGIseed Dashboard/i);

  // Check experiment selector and summary cards
  await expect(page.locator('#gate-select')).toBeVisible();
  await expect(page.locator('text=Total portes')).toBeVisible();

  // Open Academy tab
  await page.locator('button', { hasText: 'academy' }).click();
  await expect(page.locator('h2')).toHaveText(/Academy/i);

  // Ensure academy content loads from API
  const versionList = page.locator('.academy-box ol li');
  await expect(versionList.first()).toBeVisible();

  // Check comparison chart is rendered
  await page.locator('button', { hasText: 'comparison' }).click();
  await expect(page.locator('text=Fitness finale')).toBeVisible();
  await expect(page.locator('text=Précision finale')).toBeVisible();
  await expect(page.locator('text=Radar des performances')).toBeVisible();

  // Check topology tab shows placeholder or actual topology
  await page.locator('button', { hasText: 'topology' }).click();
  await expect(page.locator('h2')).toHaveText(/Topologie du meilleur modèle/i);
});

test('receives websocket evolution updates', async ({ page }) => {
  await page.goto(FRONTEND);
  const wsMessage = page.locator('.ws-log div', { hasText: 'fitness' });
  await expect(wsMessage).toBeVisible({ timeout: 10000 });
});
