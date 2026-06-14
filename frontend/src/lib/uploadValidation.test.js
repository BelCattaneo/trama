import { describe, expect, it } from "vitest";
import { MAX_BYTES, validateClientFile } from "./uploadValidation";

function makeFile(name, size, type) {
  return new File([new Uint8Array(size)], name, { type });
}

describe("validateClientFile", () => {
  it("accepts a pdf by mime type", () => {
    expect(
      validateClientFile(makeFile("x.pdf", 100, "application/pdf")),
    ).toEqual({
      ok: true,
    });
  });

  it("accepts a csv by mime type", () => {
    expect(validateClientFile(makeFile("x.csv", 100, "text/csv"))).toEqual({
      ok: true,
    });
  });

  it("accepts when mime is missing but extension matches", () => {
    expect(validateClientFile(makeFile("planilla.xlsx", 100, ""))).toEqual({
      ok: true,
    });
  });

  it("rejects when neither mime nor extension matches", () => {
    const result = validateClientFile(makeFile("notes.txt", 100, "text/plain"));
    expect(result.ok).toBe(false);
    expect(result.error).toMatch(/formato no soportado/i);
  });

  it("rejects when over the size cap", () => {
    const result = validateClientFile(
      makeFile("big.pdf", MAX_BYTES + 1, "application/pdf"),
    );
    expect(result.ok).toBe(false);
    expect(result.error).toMatch(/muy grande.*10 mb/i);
  });

  it("accepts exactly at the size cap", () => {
    expect(
      validateClientFile(makeFile("limit.pdf", MAX_BYTES, "application/pdf")),
    ).toEqual({ ok: true });
  });
});
