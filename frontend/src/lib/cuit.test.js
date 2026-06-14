import { describe, expect, it } from "vitest";
import { formatCuit, isValidCuitFormat } from "./cuit";

describe("formatCuit", () => {
  it("returns empty string when input has no digits", () => {
    expect(formatCuit("")).toBe("");
    expect(formatCuit("abc")).toBe("");
  });

  it("does not insert dash for the first two digits", () => {
    expect(formatCuit("2")).toBe("2");
    expect(formatCuit("20")).toBe("20");
  });

  it("inserts the first dash after the second digit", () => {
    expect(formatCuit("201")).toBe("20-1");
    expect(formatCuit("2012345")).toBe("20-12345");
  });

  it("inserts the second dash before the check digit", () => {
    expect(formatCuit("20123456786")).toBe("20-12345678-6");
  });

  it("strips existing dashes and reformats", () => {
    expect(formatCuit("20-12345678-6")).toBe("20-12345678-6");
    expect(formatCuit("20.12345678.6")).toBe("20-12345678-6");
  });

  it("ignores digits past the 11th", () => {
    expect(formatCuit("201234567899999")).toBe("20-12345678-9");
  });
});

describe("isValidCuitFormat", () => {
  it("accepts canonical XX-XXXXXXXX-X format", () => {
    expect(isValidCuitFormat("20-12345678-6")).toBe(true);
  });

  it("accepts 11-digit dashless format", () => {
    expect(isValidCuitFormat("20123456786")).toBe(true);
  });

  it("rejects shorter strings", () => {
    expect(isValidCuitFormat("20-1234567-6")).toBe(false);
  });

  it("rejects non-digit characters", () => {
    expect(isValidCuitFormat("abc")).toBe(false);
  });
});
