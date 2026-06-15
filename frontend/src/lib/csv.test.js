import { describe, expect, it } from "vitest";
import { buildOperationCsv, buildOperationFilename } from "./csv";

describe("buildOperationCsv", () => {
  it("includes BOM and header row", () => {
    const csv = buildOperationCsv([
      { product: "tomate", quantity: 5, unit: "kg" },
    ]);
    expect(csv.startsWith("﻿")).toBe(true);
    expect(csv).toContain("producto,cantidad,unidad");
  });

  it("renders each line in original order", () => {
    const csv = buildOperationCsv([
      { product: "a", quantity: 1, unit: "kg" },
      { product: "b", quantity: 2, unit: "kg" },
      { product: "c", quantity: 3, unit: "kg" },
    ]);
    const lines = csv.replace("﻿", "").trim().split("\n");
    expect(lines[1]).toBe("a,1,kg");
    expect(lines[2]).toBe("b,2,kg");
    expect(lines[3]).toBe("c,3,kg");
  });

  it("escapes commas by wrapping the field in double quotes", () => {
    const csv = buildOperationCsv([
      { product: "tomate cherry, mini", quantity: 1, unit: "kg" },
    ]);
    expect(csv).toContain('"tomate cherry, mini",1,kg');
  });

  it("escapes internal double quotes by doubling them", () => {
    const csv = buildOperationCsv([
      { product: 'producto "raro"', quantity: 1, unit: "kg" },
    ]);
    expect(csv).toContain('"producto ""raro""",1,kg');
  });

  it("escapes newlines inside a field", () => {
    const csv = buildOperationCsv([
      { product: "tomate\nperita", quantity: 1, unit: "kg" },
    ]);
    expect(csv).toContain('"tomate\nperita",1,kg');
  });

  it("renders null unit as empty string", () => {
    const csv = buildOperationCsv([
      { product: "tomate", quantity: 1, unit: null },
    ]);
    expect(csv).toContain("tomate,1,");
  });
});

describe("buildOperationFilename", () => {
  it("uses 'pedido' prefix for kind=order", () => {
    expect(
      buildOperationFilename({
        kind: "order",
        operationDate: "2026-06-15",
        id: "a1b2c3d4e5f6",
      }),
    ).toBe("pedido_2026-06-15_a1b2c3d4.csv");
  });

  it("uses 'oferta' prefix for kind=offer", () => {
    expect(
      buildOperationFilename({
        kind: "offer",
        operationDate: "2026-06-15",
        id: "abcdef0123456789",
      }),
    ).toBe("oferta_2026-06-15_abcdef01.csv");
  });

  it("falls back to 'pedido' for unknown kind", () => {
    expect(
      buildOperationFilename({
        kind: "weird",
        operationDate: "2026-06-15",
        id: "12345678aaa",
      }),
    ).toBe("pedido_2026-06-15_12345678.csv");
  });

  it("uses only first 8 chars of id", () => {
    const filename = buildOperationFilename({
      kind: "order",
      operationDate: "2026-06-15",
      id: "very-long-uuid-string",
    });
    expect(filename).toMatch(/_very-lon\.csv$/);
  });
});
