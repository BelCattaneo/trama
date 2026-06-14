import { describe, expect, it } from "vitest";
import { operationLabels } from "./roleLabels";

describe("operationLabels", () => {
  it("returns producer labels for role 'producer'", () => {
    expect(operationLabels("producer")).toEqual({
      nav: "Mi oferta",
      action: "Subir oferta",
      firstAction: "Subir tu primera oferta",
    });
  });

  it("returns consumer labels for role 'consumer'", () => {
    expect(operationLabels("consumer")).toEqual({
      nav: "Mis pedidos",
      action: "Subir pedido",
      firstAction: "Subir tu primer pedido",
    });
  });

  it("returns both/operation labels for role 'both'", () => {
    expect(operationLabels("both")).toEqual({
      nav: "Mis operaciones",
      action: "Subir operación",
      firstAction: "Subir tu primera operación",
    });
  });

  it("returns both/operation labels for undefined role", () => {
    expect(operationLabels(undefined).nav).toBe("Mis operaciones");
  });
});
