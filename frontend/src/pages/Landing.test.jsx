import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import Landing from "./Landing";

function renderLanding() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <Landing />
    </MemoryRouter>,
  );
}

describe("Landing", () => {
  it("renders the headline", () => {
    renderLanding();
    expect(
      screen.getByRole("heading", { name: /la red que conecta/i }),
    ).toBeInTheDocument();
  });

  it("renders the description", () => {
    renderLanding();
    expect(screen.getByText(/subí tu lista de pedidos/i)).toBeInTheDocument();
  });

  it("renders signup and login CTAs in the hero", () => {
    renderLanding();
    const hero = screen.getByRole("main");
    expect(
      within(hero).getByRole("link", { name: /^crear cuenta$/i }),
    ).toBeInTheDocument();
    expect(
      within(hero).getByRole("link", { name: /^iniciar sesión$/i }),
    ).toBeInTheDocument();
  });
});
