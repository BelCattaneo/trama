import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import App from "./App";
import { AuthProvider } from "./contexts/AuthContext";

function renderAt(path, initialUser = null) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider initialUser={initialUser}>
        <App />
      </AuthProvider>
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

  it("renders the signup page on /signup when anonymous", () => {
    renderAt("/signup");
    expect(
      screen.getByRole("heading", { name: /creá tu cuenta/i }),
    ).toBeInTheDocument();
  });

  it("renders the login page on /login when anonymous", () => {
    renderAt("/login");
    expect(
      screen.getByRole("heading", { name: /iniciá sesión/i }),
    ).toBeInTheDocument();
  });

  it("redirects authenticated users away from /login to /upload", () => {
    renderAt("/login", {
      user: { id: "u", email: "demo@example.com" },
      node: {
        id: "n",
        display_name: "Cooperativa Demo",
        role: "consumer",
      },
    });
    expect(
      screen.getByRole("heading", { name: /subir pedido/i }),
    ).toBeInTheDocument();
  });

  it("bumps anonymous users from /upload back to /login", () => {
    renderAt("/upload");
    expect(
      screen.getByRole("heading", { name: /iniciá sesión/i }),
    ).toBeInTheDocument();
  });
});
