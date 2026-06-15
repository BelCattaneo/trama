import { test, expect } from "@playwright/test";
import { signupAndLogin } from "./helpers/auth.js";

test("auth: signup, session persistence, logout, guard, login", async ({
  page,
}) => {
  const { email, password } = await signupAndLogin(page, { tag: "auth" });

  await page.reload();
  await expect(page).toHaveURL(/\/upload/);

  await page.getByRole("button", { name: "Salir" }).click();
  await expect(page).toHaveURL(/\/login/);

  await page.goto("/upload");
  await expect(page).toHaveURL(/\/login/);

  await page.locator("#login-email").fill(email);
  await page.locator("#login-password").fill(password);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page).toHaveURL(/\/upload/);
});
