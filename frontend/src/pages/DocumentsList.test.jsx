import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../contexts/AuthContext";
import DocumentsList from "./DocumentsList";

const USER = {
  user: { id: "u", email: "demo@example.com", full_name: "Demo" },
  node: { id: "n", display_name: "Cooperativa Demo" },
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/mis-documentos"]}>
      <AuthProvider initialUser={USER}>
        <Routes>
          <Route path="/mis-documentos" element={<DocumentsList />} />
          <Route path="/upload" element={<div>upload page</div>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.spyOn(global, "fetch").mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("DocumentsList", () => {
  it("shows loading state while fetching", () => {
    global.fetch.mockImplementation(() => new Promise(() => {}));
    renderPage();
    expect(screen.getByRole("status")).toHaveTextContent(/cargando/i);
  });

  it("renders empty state with CTA on 200 + 0 docs", async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ documents: [] }),
    });
    renderPage();
    await waitFor(() => {
      expect(
        screen.getByText(/todavía no subiste documentos/i),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByRole("link", { name: /subir tu primer pedido/i }),
    ).toBeInTheDocument();
  });

  it("renders a row per document on 200 + N docs", async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        documents: [
          {
            id: "d1",
            original_filename: "pedido-enero.xlsx",
            mime_type:
              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            uploaded_at: "2026-03-17T12:00:00Z",
          },
          {
            id: "d2",
            original_filename: "foto.png",
            mime_type: "image/png",
            uploaded_at: "2026-03-16T12:00:00Z",
          },
          {
            id: "d3",
            original_filename: "lista.pdf",
            mime_type: "application/pdf",
            uploaded_at: "2026-03-15T12:00:00Z",
          },
        ],
      }),
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("pedido-enero.xlsx")).toBeInTheDocument();
    });
    expect(screen.getByText("foto.png")).toBeInTheDocument();
    expect(screen.getByText("lista.pdf")).toBeInTheDocument();
    expect(screen.getByText("Planilla Excel")).toBeInTheDocument();
    expect(screen.getByText("Imagen")).toBeInTheDocument();
    expect(screen.getByText("PDF")).toBeInTheDocument();
  });

  it("renders error card on non-ok response", async () => {
    global.fetch.mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({}),
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        /no pudimos cargar tus documentos/i,
      );
    });
  });

  it("renders error card on network failure", async () => {
    global.fetch.mockRejectedValue(new Error("network down"));
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        /no pudimos cargar tus documentos/i,
      );
    });
  });

  it("header 'Subir pedido' CTA navigates to /upload", async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ documents: [] }),
    });
    const { container } = renderPage();
    await waitFor(() => {
      expect(container.querySelector(".docs-page__cta")).toBeInTheDocument();
    });
    fireEvent.click(container.querySelector(".docs-page__cta"));
    expect(screen.getByText(/upload page/i)).toBeInTheDocument();
  });

  it("empty-state CTA navigates to /upload", async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ documents: [] }),
    });
    renderPage();
    await waitFor(() => {
      expect(
        screen.getByRole("link", { name: /subir tu primer pedido/i }),
      ).toBeInTheDocument();
    });
    fireEvent.click(
      screen.getByRole("link", { name: /subir tu primer pedido/i }),
    );
    expect(screen.getByText(/upload page/i)).toBeInTheDocument();
  });
});
