import { test, expect } from "@playwright/test";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { signupAndLogin } from "./helpers/auth.js";

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
}

test.describe("review flows", () => {
  test("scenario 1: xlsx happy path → confirm → my-orders highlight", async ({
    page,
  }) => {
    await signupAndLogin(page, { tag: "rev1" });
    await uploadAndGoToReview(page, path.join(FIXTURES, "clean_table.xlsx"));

    await expect(page.locator(".review-page__line").first()).toBeVisible();
    await expect(page.locator(".review-page__line")).toHaveCount(3);
    await expect(page.getByText("Descargar original")).toBeVisible();
    await expect(page.locator(".review-page__preview-image")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Confirmar" })).toBeEnabled();

    await page.getByRole("button", { name: "Confirmar" }).click();
    await expect(page).toHaveURL(/\/my-orders\?highlight=[0-9a-f-]{36}/);
    await expect(page.locator(".highlighted-row").first()).toBeVisible();
  });

  test("scenario 2: jpeg with LLM stub clean → edit quantity → confirm", async ({
    page,
  }) => {
    await signupAndLogin(page, { tag: "rev2" });
    await page.setExtraHTTPHeaders(stubHeader(CLEAN_PAYLOAD));

    await uploadAndGoToReview(page, path.join(FIXTURES, "clean_photo.jpg"));
    await expect(page.locator(".review-page__preview-image")).toBeVisible();
    await expect(page.locator(".review-page__line")).toHaveCount(3);

    const firstQty = page.locator("[id^='line-'][id$='-quantity']").first();
    await firstQty.fill("7");

    await expect(page.getByRole("button", { name: "Confirmar" })).toBeEnabled();
    await page.getByRole("button", { name: "Confirmar" }).click();
    await expect(page).toHaveURL(/\/my-orders\?highlight=[0-9a-f-]{36}/);
    await expect(page.locator(".highlighted-row").first()).toBeVisible();
  });

  test("scenario 3: 3-page pdf with stubbed LLM per page → tabs filter", async ({
    page,
  }) => {
    await signupAndLogin(page, { tag: "rev3" });
    const perPage = [
      { lines: [{ product: "tomate", quantity: 5, unit: "kg" }], warnings: [] },
      {
        lines: [{ product: "cebolla", quantity: 3, unit: "atados" }],
        warnings: [],
      },
      {
        lines: [{ product: "zanahoria", quantity: 2, unit: "kg" }],
        warnings: ["alerta de prueba"],
      },
    ];
    await page.setExtraHTTPHeaders(stubHeader(perPage));

    await uploadAndGoToReview(page, path.join(FIXTURES, "multi_page.pdf"));

    await expect(page.getByRole("tab", { name: "Página 1" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "Página 2" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "Página 3" })).toBeVisible();
    await expect(
      page.getByRole("tab", { name: "Todas las páginas" }),
    ).toBeVisible();

    // start filtered on page 1 → only 1 line, no warnings
    await expect(page.locator(".review-page__line")).toHaveCount(1);
    await expect(page.locator(".review-page__line").first()).toContainText(
      "tomate",
    );

    await page.getByRole("tab", { name: "Página 3" }).click();
    await expect(page.locator(".review-page__line").first()).toContainText(
      "zanahoria",
    );
    await expect(page.getByText("[p3] alerta de prueba")).toBeVisible();

    await page.getByRole("tab", { name: "Todas las páginas" }).click();
    await expect(page.locator(".review-page__line")).toHaveCount(3);

    await page.getByRole("button", { name: "Confirmar" }).click();
    await expect(page).toHaveURL(/\/my-orders\?highlight=[0-9a-f-]{36}/);
  });

  test("scenario 4: heic preview decodes to img", async ({ page }) => {
    await signupAndLogin(page, { tag: "rev4" });
    await page.setExtraHTTPHeaders(stubHeader(CLEAN_PAYLOAD));

    await uploadAndGoToReview(page, path.join(FIXTURES, "iphone_photo.heic"));
    await expect(page.locator(".review-page__preview-image")).toBeVisible({
      timeout: 15_000,
    });
  });

  test("scenario 5: confidence=0 → red banner → add 3 lines → confirm", async ({
    page,
  }) => {
    await signupAndLogin(page, { tag: "rev5" });
    await page.setExtraHTTPHeaders(
      stubHeader({ __raise__: true, message: "forced failure" }),
    );

    await uploadAndGoToReview(page, path.join(FIXTURES, "clean_photo.jpg"));

    await expect(page.locator(".review-page__banner--error")).toBeVisible();

    const addBtn = page.getByRole("button", { name: /agregar línea/i });
    for (let i = 0; i < 3; i++) await addBtn.click();
    await expect(page.locator(".review-page__line")).toHaveCount(3);

    const products = page.locator("[id^='line-'][id$='-product']");
    const qties = page.locator("[id^='line-'][id$='-quantity']");
    const units = page.locator("[id^='line-'][id$='-unit']");
    const items = [
      ["tomate", "5", "kg"],
      ["cebolla", "3", "atados"],
      ["zanahoria", "2", "kg"],
    ];
    for (let i = 0; i < 3; i++) {
      await products.nth(i).fill(items[i][0]);
      await qties.nth(i).fill(items[i][1]);
      await units.nth(i).fill(items[i][2]);
    }

    await expect(page.getByRole("button", { name: "Confirmar" })).toBeEnabled();
    await page.getByRole("button", { name: "Confirmar" }).click();
    await expect(page).toHaveURL(/\/my-orders\?highlight=[0-9a-f-]{36}/);
  });

  test("scenario 6: unreadable markers → confirm disabled until fixed", async ({
    page,
  }) => {
    await signupAndLogin(page, { tag: "rev6" });
    await page.setExtraHTTPHeaders(
      stubHeader({
        lines: [
          { product: "unreadable", quantity: 0, unit: null },
          { product: "tomate", quantity: 5, unit: "kg" },
        ],
        warnings: [],
      }),
    );

    await uploadAndGoToReview(page, path.join(FIXTURES, "clean_photo.jpg"));

    await expect(page.locator(".review-page__line--warn")).toHaveCount(1);
    await expect(
      page.getByRole("button", { name: "Confirmar" }),
    ).toBeDisabled();

    const firstProduct = page.locator("[id^='line-'][id$='-product']").first();
    const firstQty = page.locator("[id^='line-'][id$='-quantity']").first();
    await firstProduct.fill("papa");
    await firstQty.fill("4");

    await expect(page.getByRole("button", { name: "Confirmar" })).toBeEnabled();
    await page.getByRole("button", { name: "Confirmar" }).click();
    await expect(page).toHaveURL(/\/my-orders\?highlight=[0-9a-f-]{36}/);
  });

  test("scenario 7: already confirmed → blue banner + read-only + no confirm", async ({
    page,
  }) => {
    await signupAndLogin(page, { tag: "rev7" });
    await uploadAndGoToReview(page, path.join(FIXTURES, "clean_table.xlsx"));
    const reviewUrl = page.url();
    await page.getByRole("button", { name: "Confirmar" }).click();
    await expect(page).toHaveURL(/\/my-orders/);

    await page.goto(reviewUrl);
    await expect(page.locator(".review-page__banner--info")).toBeVisible();
    await expect(page.getByRole("button", { name: "Confirmar" })).toHaveCount(
      0,
    );
    const firstProduct = page.locator("[id^='line-'][id$='-product']").first();
    await expect(firstProduct).toBeDisabled();
  });

  test("scenario 8: nav guard → confirm dialog on unsaved changes", async ({
    page,
  }) => {
    await signupAndLogin(page, { tag: "rev8" });
    await uploadAndGoToReview(page, path.join(FIXTURES, "clean_table.xlsx"));

    const firstQty = page.locator("[id^='line-'][id$='-quantity']").first();
    await firstQty.fill("99");

    page.once("dialog", async (dialog) => {
      expect(dialog.message()).toContain("salir sin confirmar");
      await dialog.dismiss();
    });
    await page.getByRole("link", { name: "Mis pedidos" }).click();
    await expect(page).toHaveURL(/\/review\/[0-9a-f-]{36}/);
  });
});
