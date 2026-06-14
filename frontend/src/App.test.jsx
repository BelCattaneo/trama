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
  it("renders the landing headline on /", () => {
    renderAt("/");
    expect(
      screen.getByRole("heading", { name: /la red que conecta/i }),
    ).toBeInTheDocument();
  });

  it("renders the signup page on /signup", () => {
    renderAt("/signup");
    expect(
      screen.getByRole("heading", { name: /creá tu cuenta/i }),
    ).toBeInTheDocument();
  });

  it("renders the login page on /login", () => {
    renderAt("/login");
    expect(
      screen.getByRole("heading", { name: /iniciá sesión/i }),
    ).toBeInTheDocument();
  });
});
