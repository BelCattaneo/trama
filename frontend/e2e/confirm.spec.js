import { test, expect } from "@playwright/test";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { signupAndLogin, login } from "./helpers/auth.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FIXTURES = path.join(__dirname, "fixtures", "review");

const CLEAN_PAYLOAD = {
  lines: [
    { product: "tomate", quantity: 5, unit: "kg" },
    { product: "cebolla", quantity: 3, unit: "atados" },
    { product: "zanahoria", quantity: 2, unit: "kg" },
  ],
  warnings: [],
};

function stubHeader(payload) {
  return { "X-LLM-Stub-Response": JSON.stringify(payload) };
}

async function uploadAndGoToReview(page, fixturePath) {
  await page.locator('input[type="file"]').setInputFiles(fixturePath);
  await expect(page).toHaveURL(/\/review\/[0-9a-f-]{36}/);
  return page.url().match(/\/review\/([0-9a-f-]{36})/)[1];
}

test.describe("confirm flows", () => {
  test("scenario 9: unauthenticated /review/:id → redirect to /login", async ({
    page,
  }) => {
    const fakeId = "00000000-0000-0000-0000-000000000000";
    await page.goto(`/review/${fakeId}`);
    await expect(page).toHaveURL(/\/login/);
  });

  test("scenario 10: document of another node → 404 → bounced to /upload", async ({
    browser,
  }) => {
    const ctxA = await browser.newContext();
    const pageA = await ctxA.newPage();
    await signupAndLogin(pageA, { tag: "u-a" });
    const docId = await uploadAndGoToReview(
      pageA,
      path.join(FIXTURES, "clean_table.xlsx"),
    );
    await ctxA.close();

    const ctxB = await browser.newContext();
    const pageB = await ctxB.newPage();
    await signupAndLogin(pageB, { tag: "u-b" });
    await pageB.goto(`/review/${docId}`);
    // 404 surfaces as the error state in the Review component.
    await expect(
      pageB.getByText("No pudimos cargar el documento."),
    ).toBeVisible();
    await ctxB.close();
  });

  test("scenario 11: race confirm 409 → toast 'ya confirmado'", async ({
    browser,
  }) => {
    const ctxA = await browser.newContext();
    const pageA = await ctxA.newPage();
    const creds = await signupAndLogin(pageA, { tag: "race" });
    const docId = await uploadAndGoToReview(
      pageA,
      path.join(FIXTURES, "clean_table.xlsx"),
    );

    const ctxB = await browser.newContext();
    const pageB = await ctxB.newPage();
    await login(pageB, creds);
    await pageB.goto(`/review/${docId}`);
    await expect(
      pageB.getByRole("button", { name: "Confirmar" }),
    ).toBeEnabled();

    // confirm first in A
    await pageA.getByRole("button", { name: "Confirmar" }).click();
    await expect(pageA).toHaveURL(/\/my-orders/);

    // confirm second in B — backend rejects with 409
    await pageB.getByRole("button", { name: "Confirmar" }).click();
    await expect(pageB.locator(".review-page__toast")).toContainText(
      "ya confirmado",
    );
    await expect(pageB).toHaveURL(/\/review\//);

    await ctxA.close();
    await ctxB.close();
  });

  test("scenario 12: backend 500 on confirm → generic toast → state preserved", async ({
    page,
  }) => {
    await signupAndLogin(page, { tag: "err500" });
    const docId = await uploadAndGoToReview(
      page,
      path.join(FIXTURES, "clean_table.xlsx"),
    );

    // Force a single 500 on the confirm endpoint via Playwright route().
    let blocked = false;
    await page.route(`**/api/documents/${docId}/confirm`, async (route) => {
      if (!blocked) {
        blocked = true;
        await route.fulfill({
          status: 500,
          contentType: "application/json",
          body: JSON.stringify({ error: "internal server error" }),
        });
        return;
      }
      await route.continue();
    });

    await page.getByRole("button", { name: "Confirmar" }).click();
    await expect(page.locator(".review-page__toast")).toBeVisible();
    await expect(page).toHaveURL(/\/review\//);
  });

  test("scenario 13: PDF >10 pages → warning + 10 page tabs only", async ({
    page,
  }) => {
    await signupAndLogin(page, { tag: "huge" });
    // The orchestrator caps at 10 pages; canned responses for 10 pages.
    const perPage = Array.from({ length: 10 }, (_, i) => ({
      lines: [{ product: `prod${i + 1}`, quantity: 1, unit: "kg" }],
      warnings: [],
    }));
    await page.setExtraHTTPHeaders(stubHeader(perPage));

    await uploadAndGoToReview(page, path.join(FIXTURES, "huge.pdf"));

    // PageTabs falls back to a <select> when totalPages > 5; the option list
    // should be exactly 10 pages + "Todas".
    await expect(page.locator("#review-page-select option")).toHaveCount(11);
    await expect(
      page.locator("#review-page-select option[value='11']"),
    ).toHaveCount(0);

    // The truncation warning is not page-scoped → only visible when "Todas".
    await page.locator("#review-page-select").selectOption("all");
    await expect(page.getByText(/PDF tiene más de 10 páginas/)).toBeVisible();
  });
});
