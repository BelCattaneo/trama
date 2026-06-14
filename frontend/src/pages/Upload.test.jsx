import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../contexts/AuthContext";
import Upload from "./Upload";

function renderUpload() {
  return render(
    <MemoryRouter initialEntries={["/upload"]}>
      <AuthProvider
        initialUser={{
          user: { id: "u", email: "demo@example.com", full_name: "Demo" },
          node: {
            id: "n",
            display_name: "Cooperativa Demo",
            role: "consumer",
          },
        }}
      >
        <Routes>
          <Route path="/upload" element={<Upload />} />
          <Route path="/documents" element={<div>documents page</div>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

function makeFile(name, size, type) {
  const file = new File([new Uint8Array(size)], name, { type });
  return file;
}

beforeEach(() => {
  vi.spyOn(global, "fetch").mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("Upload", () => {
  it("renders idle drop zone and formats hint", () => {
    renderUpload();
    expect(
      screen.getByRole("heading", { name: /subir pedido/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/arrastrá tu archivo acá/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /elegir archivo/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/formatos aceptados.*xlsx.*csv.*jpg.*png.*pdf/i),
    ).toBeInTheDocument();
  });

  it("rejects unsupported format without POSTing", () => {
    renderUpload();
    const input = screen.getByLabelText(/seleccionar archivo/i);
    const file = makeFile("note.txt", 10, "text/plain");
    fireEvent.change(input, { target: { files: [file] } });
    expect(screen.getByRole("alert")).toHaveTextContent(
      /formato no soportado/i,
    );
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("rejects file > 10 MB without POSTing", () => {
    renderUpload();
    const input = screen.getByLabelText(/seleccionar archivo/i);
    const file = makeFile("big.pdf", 11 * 1024 * 1024, "application/pdf");
    fireEvent.change(input, { target: { files: [file] } });
    expect(screen.getByRole("alert")).toHaveTextContent(/muy grande.*10 mb/i);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("highlights drop zone on dragOver", () => {
    renderUpload();
    const drop = screen.getByText(/arrastrá tu archivo acá/i).parentElement;
    fireEvent.dragOver(drop);
    expect(drop.className).toMatch(/upload-page__drop--active/);
    fireEvent.dragLeave(drop);
    expect(drop.className).not.toMatch(/upload-page__drop--active/);
  });

  it("navigates to /documents on 201", async () => {
    global.fetch.mockResolvedValue({
      status: 201,
      ok: true,
      json: async () => ({ id: "doc-1" }),
    });
    renderUpload();
    const input = screen.getByLabelText(/seleccionar archivo/i);
    const file = makeFile("pedido.pdf", 1024, "application/pdf");
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => {
      expect(screen.getByText(/documents page/i)).toBeInTheDocument();
    });
    expect(global.fetch).toHaveBeenCalledWith(
      "/api/documents",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("shows backend 400 error message", async () => {
    global.fetch.mockResolvedValue({
      status: 400,
      ok: false,
      json: async () => ({ error: "El archivo está vacío" }),
    });
    renderUpload();
    const input = screen.getByLabelText(/seleccionar archivo/i);
    const file = makeFile("pedido.pdf", 1024, "application/pdf");
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        /el archivo está vacío/i,
      );
    });
  });

  it("shows generic error on network failure", async () => {
    global.fetch.mockRejectedValue(new Error("network down"));
    renderUpload();
    const input = screen.getByLabelText(/seleccionar archivo/i);
    const file = makeFile("pedido.pdf", 1024, "application/pdf");
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        /no pudimos subir el archivo/i,
      );
    });
  });
});
