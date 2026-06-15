import { test, expect } from "@playwright/test";
import { fileURLToPath } from "node:url";
import path from "node:path";

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

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FIXTURE_PATH = path.join(__dirname, "fixtures", "sample.xlsx");

test("upload: signup, select xlsx, land on documents list with file visible", async ({
  page,
}) => {
  const stamp = Date.now();
  const email = `e2e+upload${stamp}@trama.test`;
  const password = "test1234";
  const cuit = generateValidCuit();
  const displayName = `Mutual Upload ${stamp}`;

  await page.goto("/signup");
  await page.locator("#signup-cuit").fill(cuit);
  await page.locator("#signup-email").fill(email);
  await page.locator("#signup-password").fill(password);
  await page.locator("#signup-display-name").fill(displayName);
  await page.locator("#signup-address").fill("Av Corrientes 1234, CABA");
  await page.getByRole("button", { name: "Crear cuenta" }).click();

  await expect(page).toHaveURL(/\/upload/);

  await page.locator('input[type="file"]').setInputFiles(FIXTURE_PATH);

  await expect(page).toHaveURL(/\/documents/);
  await expect(page.getByRole("cell", { name: "sample.xlsx" })).toBeVisible();
});
