import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import Signup from "./Signup";

function renderSignup() {
  return render(
    <MemoryRouter initialEntries={["/signup"]}>
      <Routes>
        <Route path="/signup" element={<Signup />} />
        <Route path="/upload" element={<div>upload landing</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

const VALID = {
  cuit: "20-12345678-6",
  email: "demo@example.com",
  password: "secret",
  display_name: "Mutual Demo",
  address: "Calle Falsa 123",
};

function fillForm() {
  fireEvent.change(screen.getByLabelText(/^CUIT$/i), {
    target: { value: VALID.cuit },
  });
  fireEvent.change(screen.getByLabelText(/^Email$/i), {
    target: { value: VALID.email },
  });
  fireEvent.change(screen.getByLabelText(/^Contraseña$/i), {
    target: { value: VALID.password },
  });
  fireEvent.change(screen.getByLabelText(/Nombre del nodo/i), {
    target: { value: VALID.display_name },
  });
  fireEvent.change(screen.getByLabelText(/^Dirección$/i), {
    target: { value: VALID.address },
  });
}

beforeEach(() => {
  vi.spyOn(global, "fetch").mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("Signup", () => {
  it("renders all required fields", () => {
    renderSignup();
    expect(screen.getByLabelText(/^CUIT$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Email$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Contraseña$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Nombre del nodo/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Dirección$/i)).toBeInTheDocument();
    expect(
      screen.getByRole("radiogroup", { name: /rol/i }),
    ).toBeInTheDocument();
  });

  it("shows required-field errors when submitting empty", async () => {
    renderSignup();
    fireEvent.click(screen.getByRole("button", { name: /crear cuenta/i }));
    expect(await screen.findAllByText(/campo requerido/i)).toHaveLength(5);
  });

  it("strips non-digits from the CUIT input as the user types", () => {
    renderSignup();
    const input = screen.getByLabelText(/^CUIT$/i);
    fireEvent.change(input, { target: { value: "abc20-12def345678!6" } });
    expect(input.value).toBe("20-12345678-6");
  });

  it("auto-formats the CUIT with dashes as the user types", () => {
    renderSignup();
    const input = screen.getByLabelText(/^CUIT$/i);
    fireEvent.change(input, { target: { value: "20123456786" } });
    expect(input.value).toBe("20-12345678-6");
  });

  it("shows CUIT format error for incomplete CUIT", () => {
    renderSignup();
    fireEvent.change(screen.getByLabelText(/^CUIT$/i), {
      target: { value: "12345" },
    });
    fireEvent.click(screen.getByRole("button", { name: /crear cuenta/i }));
    expect(
      screen.getByText(/El CUIT no tiene el formato correcto/i),
    ).toBeInTheDocument();
  });

  it("submits valid form and navigates to /upload on success", async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ node_id: "n", user_id: "u" }),
    });
    renderSignup();
    fillForm();
    fireEvent.click(screen.getByRole("button", { name: /crear cuenta/i }));
    await waitFor(() =>
      expect(screen.getByText(/upload landing/i)).toBeInTheDocument(),
    );
    expect(global.fetch).toHaveBeenCalledWith(
      "/api/auth/signup",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
      }),
    );
    const body = JSON.parse(global.fetch.mock.calls[0][1].body);
    expect(body.cuit).toBe(VALID.cuit);
    expect(body.role).toBe("consumer");
  });

  it("shows CUIT duplicate error from backend near the CUIT field", async () => {
    global.fetch.mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({ error: "CUIT ya registrado" }),
    });
    renderSignup();
    fillForm();
    fireEvent.click(screen.getByRole("button", { name: /crear cuenta/i }));
    expect(await screen.findByText(/CUIT ya registrado/i)).toBeInTheDocument();
  });

  it("shows email duplicate error from backend near the email field", async () => {
    global.fetch.mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({ error: "email ya registrado" }),
    });
    renderSignup();
    fillForm();
    fireEvent.click(screen.getByRole("button", { name: /crear cuenta/i }));
    expect(await screen.findByText(/email ya registrado/i)).toBeInTheDocument();
  });

  it("reveals latitude+longitude when backend reports geocoding failure", async () => {
    global.fetch.mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({
        error:
          "no se pudo ubicar la dirección, ingresá coordenadas manualmente",
      }),
    });
    renderSignup();
    fillForm();
    fireEvent.click(screen.getByRole("button", { name: /crear cuenta/i }));
    expect(await screen.findByLabelText(/Latitud/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Longitud/i)).toBeInTheDocument();
  });

  it("changes role when pill is clicked", () => {
    renderSignup();
    fireEvent.click(screen.getByRole("radio", { name: /productorx/i }));
    expect(screen.getByRole("radio", { name: /productorx/i })).toHaveAttribute(
      "aria-checked",
      "true",
    );
  });
});
