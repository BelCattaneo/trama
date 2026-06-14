import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import App from "./App";

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

describe("App routes", () => {
  it("renders trama heading on /", () => {
    renderAt("/");
    expect(screen.getByRole("heading", { name: /trama/i })).toBeInTheDocument();
  });

  it("renders the signup placeholder on /signup", () => {
    renderAt("/signup");
    expect(
      screen.getByRole("heading", { name: /crear cuenta/i }),
    ).toBeInTheDocument();
  });

  it("renders the login placeholder on /login", () => {
    renderAt("/login");
    expect(
      screen.getByRole("heading", { name: /iniciar sesión/i }),
    ).toBeInTheDocument();
  });
});
