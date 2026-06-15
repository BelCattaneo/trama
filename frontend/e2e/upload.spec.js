import { test, expect } from "@playwright/test";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { signupAndLogin } from "./helpers/auth.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FIXTURE_PATH = path.join(__dirname, "fixtures", "sample.xlsx");

test("upload: signup, select xlsx, land on review screen for that document", async ({
  page,
}) => {
  await signupAndLogin(page, { tag: "upload" });

  await page.locator('input[type="file"]').setInputFiles(FIXTURE_PATH);

  await expect(page).toHaveURL(/\/review\/[0-9a-f-]{36}/);
  await expect(page.getByRole("button", { name: "Confirmar" })).toBeVisible();
});
