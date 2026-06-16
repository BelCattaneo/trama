import { expect } from "@playwright/test";

const CUIT_WEIGHTS = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2];

export function generateValidCuit() {
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

export async function signupAndLogin(page, { tag = "e2e" } = {}) {
  const stamp = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  const email = `${tag}+${stamp}@trama.test`;
  const password = "test1234";
  const cuit = generateValidCuit();
  const displayName = `Mutual ${tag} ${stamp}`;

  await page.goto("/signup");
  await page.locator("#signup-cuit").fill(cuit);
  await page.locator("#signup-email").fill(email);
  await page.locator("#signup-password").fill(password);
  await page.locator("#signup-display-name").fill(displayName);
  await page.locator("#signup-address").fill("Av Corrientes 1234, CABA");
  await page.getByRole("button", { name: "Crear cuenta" }).click();
  await expect(page).toHaveURL(/\/my-orders/);
  await page.goto("/upload");
  return { email, password, cuit, displayName };
}

export async function login(page, { email, password }) {
  await page.goto("/login");
  await page.locator("#login-email").fill(email);
  await page.locator("#login-password").fill(password);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page).toHaveURL(/\/my-orders/);
  await page.goto("/upload");
}
