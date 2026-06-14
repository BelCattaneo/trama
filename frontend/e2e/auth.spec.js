import { test, expect } from "@playwright/test";

const CUIT_WEIGHTS = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2];

function generateValidCuit() {
  while (true) {
    const middle = Math.floor(Math.random() * 1e8)
      .toString()
      .padStart(8, "0");
    const base = `30${middle}`;
    const sum = base
      .split("")
      .reduce((acc, d, i) => acc + parseInt(d, 10) * CUIT_WEIGHTS[i], 0);
    const remainder = 11 - (sum % 11);
    if (remainder === 10) continue;
    const check = remainder === 11 ? 0 : remainder;
    return `${base.slice(0, 2)}-${base.slice(2)}-${check}`;
  }
}

test("auth: signup, session persistence, logout, guard, login", async ({
  page,
}) => {
  const stamp = Date.now();
  const email = `e2e+${stamp}@trama.test`;
  const password = "test1234";
  const cuit = generateValidCuit();
  const displayName = `Mutual E2E ${stamp}`;

  await page.goto("/signup");
  await page.locator("#signup-cuit").fill(cuit);
  await page.locator("#signup-email").fill(email);
  await page.locator("#signup-password").fill(password);
  await page.locator("#signup-display-name").fill(displayName);
  await page.locator("#signup-address").fill("Av Corrientes 1234, CABA");
  await page.getByRole("button", { name: "Crear cuenta" }).click();

  await expect(page).toHaveURL(/\/upload/);

  await page.reload();
  await expect(page).toHaveURL(/\/upload/);

  await page.getByRole("button", { name: "Cerrar sesión" }).click();
  await expect(page).toHaveURL(/\/login/);

  await page.goto("/upload");
  await expect(page).toHaveURL(/\/login/);

  await page.locator("#login-email").fill(email);
  await page.locator("#login-password").fill(password);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page).toHaveURL(/\/upload/);
});
