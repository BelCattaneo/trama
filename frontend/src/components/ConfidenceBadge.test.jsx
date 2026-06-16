import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ConfidenceBadge, { documentStatus } from "./ConfidenceBadge";

describe("documentStatus", () => {
  it("returns confirmed when has_winner is true regardless of other fields", () => {
    expect(
      documentStatus({
        hasParseAttempt: true,
        hasWinner: true,
        latestConfidence: 0,
        latestErrorMessage: "x",
      }),
    ).toBe("confirmed");
  });

  it("returns pending when there is no parse attempt", () => {
    expect(
      documentStatus({
        hasParseAttempt: false,
        hasWinner: false,
        latestConfidence: null,
        latestErrorMessage: null,
      }),
    ).toBe("pending");
  });

  it("returns error when error message is set", () => {
    expect(
      documentStatus({
        hasParseAttempt: true,
        hasWinner: false,
        latestConfidence: null,
        latestErrorMessage: "no se encontraron columnas reconocidas",
      }),
    ).toBe("error");
  });

  it("returns error when confidence is exactly 0", () => {
    expect(
      documentStatus({
        hasParseAttempt: true,
        hasWinner: false,
        latestConfidence: 0,
        latestErrorMessage: null,
      }),
    ).toBe("error");
  });

  it("returns pending when parse attempt exists but confidence is null", () => {
    expect(
      documentStatus({
        hasParseAttempt: true,
        hasWinner: false,
        latestConfidence: null,
        latestErrorMessage: null,
      }),
    ).toBe("pending");
  });

  it("returns high when confidence >= 0.8", () => {
    expect(
      documentStatus({
        hasParseAttempt: true,
        hasWinner: false,
        latestConfidence: 0.8,
        latestErrorMessage: null,
      }),
    ).toBe("high");
    expect(
      documentStatus({
        hasParseAttempt: true,
        hasWinner: false,
        latestConfidence: 1.0,
        latestErrorMessage: null,
      }),
    ).toBe("high");
  });

  it("returns medium when 0.5 <= confidence < 0.8", () => {
    expect(
      documentStatus({
        hasParseAttempt: true,
        hasWinner: false,
        latestConfidence: 0.5,
        latestErrorMessage: null,
      }),
    ).toBe("medium");
    expect(
      documentStatus({
        hasParseAttempt: true,
        hasWinner: false,
        latestConfidence: 0.7,
        latestErrorMessage: null,
      }),
    ).toBe("medium");
  });

  it("returns low when 0 < confidence < 0.5", () => {
    expect(
      documentStatus({
        hasParseAttempt: true,
        hasWinner: false,
        latestConfidence: 0.3,
        latestErrorMessage: null,
      }),
    ).toBe("low");
    expect(
      documentStatus({
        hasParseAttempt: true,
        hasWinner: false,
        latestConfidence: 0.49,
        latestErrorMessage: null,
      }),
    ).toBe("low");
  });
});

describe("ConfidenceBadge", () => {
  it("renders default label for status", () => {
    render(<ConfidenceBadge status="confirmed" />);
    expect(screen.getByText("Confirmado")).toBeInTheDocument();
  });

  it("renders override label when provided", () => {
    render(<ConfidenceBadge status="confirmed" label="Listo p/ revisar" />);
    expect(screen.getByText("Listo p/ revisar")).toBeInTheDocument();
  });

  it("renders pending label for unknown status", () => {
    render(<ConfidenceBadge status="not-a-real-status" />);
    expect(screen.getByText("Sin procesar")).toBeInTheDocument();
  });
});
