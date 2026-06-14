import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import Login from "./Login";

function renderLogin() {
  return render(
    <MemoryRouter initialEntries={["/login"]}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/upload" element={<div>upload landing</div>} />
        <Route path="/signup" element={<div>signup landing</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.spyOn(global, "fetch").mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("Login", () => {
  it("renders email + password + signup link", () => {
    renderLogin();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/contraseña/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /iniciar sesión/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /registrate/i }),
    ).toBeInTheDocument();
  });

  it("hides the login link in the nav (already on login page)", () => {
    renderLogin();
    const links = screen.queryAllByRole("link");
    const hasLoginLink = links.some((l) =>
      /^Iniciar sesión$/.test(l.textContent),
    );
    expect(hasLoginLink).toBe(false);
  });

  it("shows error when submitting empty fields", () => {
    renderLogin();
    fireEvent.click(screen.getByRole("button", { name: /iniciar sesión/i }));
    expect(
      screen.getByText(/completá email y contraseña/i),
    ).toBeInTheDocument();
  });

  it("navigates to /upload on successful login", async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true }),
    });
    renderLogin();
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "demo@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/contraseña/i), {
      target: { value: "secret" },
    });
    fireEvent.click(screen.getByRole("button", { name: /iniciar sesión/i }));
    await waitFor(() =>
      expect(screen.getByText(/upload landing/i)).toBeInTheDocument(),
    );
    expect(global.fetch).toHaveBeenCalledWith(
      "/api/auth/login",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
      }),
    );
  });

  it("shows generic error on 401", async () => {
    global.fetch.mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ error: "credenciales inválidas" }),
    });
    renderLogin();
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "demo@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/contraseña/i), {
      target: { value: "wrong" },
    });
    fireEvent.click(screen.getByRole("button", { name: /iniciar sesión/i }));
    expect(
      await screen.findByText(/credenciales inválidas/i),
    ).toBeInTheDocument();
  });
});
