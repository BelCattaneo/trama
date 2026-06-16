import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import Privacy from "./Privacy";

function renderPrivacy() {
  return render(
    <MemoryRouter initialEntries={["/privacy"]}>
      <Privacy />
    </MemoryRouter>,
  );
}

describe("Privacy", () => {
  it("renders the page title", () => {
    renderPrivacy();
    expect(
      screen.getByRole("heading", { level: 1, name: /^privacidad$/i }),
    ).toBeInTheDocument();
  });

  it("lists the data we collect", () => {
    renderPrivacy();
    expect(
      screen.getByRole("heading", {
        level: 2,
        name: /qué datos recolectamos/i,
      }),
    ).toBeInTheDocument();
    expect(screen.getByText(/email, cuit, dirección/i)).toBeInTheDocument();
  });

  it("explains the third-party Gemini data flow", () => {
    renderPrivacy();
    expect(
      screen.getByRole("heading", {
        level: 2,
        name: /con quién los compartimos/i,
      }),
    ).toBeInTheDocument();
    expect(screen.getAllByText(/google gemini/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/xlsx y csv/i).length).toBeGreaterThan(0);
  });

  it("links to the Gemini API terms", () => {
    renderPrivacy();
    const link = screen.getByRole("link", {
      name: /términos de servicio de gemini api/i,
    });
    expect(link).toHaveAttribute(
      "href",
      "https://ai.google.dev/gemini-api/terms",
    );
  });

  it("states that trama never sells data", () => {
    renderPrivacy();
    expect(
      screen.getByText(/nunca vende datos a terceros/i),
    ).toBeInTheDocument();
  });

  it("describes user rights", () => {
    renderPrivacy();
    expect(
      screen.getByRole("heading", { level: 2, name: /tus derechos/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/eliminar tu cuenta y todos los datos/i),
    ).toBeInTheDocument();
  });
});
