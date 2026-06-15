import { test, expect } from '@playwright/test';

const FRONTEND = process.env.FRONTEND_URL || 'http://localhost:4173';

// E2E "coquille" : on vérifie ce qui est DÉTERMINISTE en CI — le shell, la navigation par
// onglets et le routing par hash — sans dépendre de l'API (en CI le backend dockerisé n'est
// pas joignable depuis le navigateur du runner, et results/ est vide). La vérification des
// données réelles (A/B, métriques) se fait en local contre un backend joignable.

test('charge le shell et navigue entre les onglets', async ({ page }) => {
  await page.goto(FRONTEND);
  await expect(page.locator('h1')).toHaveText(/AGIseed Dashboard/i);
  await expect(page.getByRole('button', { name: /Basculer le thème/i })).toBeVisible();

  // Comparaison : la sidebar (sélection de porte) et la bascule A/B sont rendues sans données.
  await page.getByTestId('tab-comparison').click();
  await expect(page).toHaveURL(/#\/comparison/);
  await expect(page.locator('#gate-select')).toBeVisible();
  await expect(page.getByText('A/B rigoureux')).toBeVisible();

  // Academy : le titre est rendu avant tout fetch.
  await page.getByTestId('tab-academy').click();
  await expect(page).toHaveURL(/#\/academy/);
  await expect(page.locator('h2')).toHaveText(/Academy/i);

  // Sandbox : l'onglet se monte (le lanceur de runs est rendu côté shell).
  await page.getByTestId('tab-sandbox').click();
  await expect(page).toHaveURL(/#\/sandbox/);
});

test('le hash est bookmarkable (deep-link direct sur un onglet)', async ({ page }) => {
  await page.goto(`${FRONTEND}/#/comparison`);
  await expect(page.getByText('A/B rigoureux')).toBeVisible();
  await expect(page.locator('#gate-select')).toBeVisible();
});
