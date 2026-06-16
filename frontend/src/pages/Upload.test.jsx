import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import {
  MemoryRouter,
  Route,
  Routes,
  useLocation,
  useParams,
} from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../contexts/AuthContext";
import Upload from "./Upload";

function LoginStub() {
  const location = useLocation();
  return <div>login page · {location.state?.message ?? ""}</div>;
}

function ReviewStub() {
  const { document_id } = useParams();
  return <div>review page · {document_id}</div>;
}

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
          <Route path="/review/:document_id" element={<ReviewStub />} />
          <Route path="/login" element={<LoginStub />} />
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

  it("discloses that photos and PDFs are sent to Google Gemini", () => {
    renderUpload();
    expect(
      screen.getByText(
        /fotos, imágenes.*heic.*pdfs se envían a google gemini/i,
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/archivos xlsx y csv se procesan localmente/i),
    ).toBeInTheDocument();
    const link = screen.getByRole("link", { name: /más info/i });
    expect(link).toHaveAttribute("href", "/privacy");
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

  it("navigates to /review/:document_id on 201", async () => {
    global.fetch.mockResolvedValue({
      status: 201,
      ok: true,
      json: async () => ({
        document: { id: "doc-1", mime_type: "application/pdf" },
        parse_attempt: null,
      }),
    });
    renderUpload();
    const input = screen.getByLabelText(/seleccionar archivo/i);
    const file = makeFile("pedido.pdf", 1024, "application/pdf");
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => {
      expect(screen.getByText(/review page · doc-1/i)).toBeInTheDocument();
    });
    expect(global.fetch).toHaveBeenCalledWith(
      "/api/documents",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("navigates to /review/:document_id on 201 even when confidence is 0", async () => {
    global.fetch.mockResolvedValue({
      status: 201,
      ok: true,
      json: async () => ({
        document: { id: "doc-zero", mime_type: "application/pdf" },
        parse_attempt: {
          id: "att-1",
          strategy: "deterministic",
          confidence: 0,
          payload: null,
          error_message: "no se encontraron columnas reconocidas",
        },
      }),
    });
    renderUpload();
    const input = screen.getByLabelText(/seleccionar archivo/i);
    const file = makeFile("pedido.pdf", 1024, "application/pdf");
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => {
      expect(screen.getByText(/review page · doc-zero/i)).toBeInTheDocument();
    });
  });

  it("shows backend 400 error message and does not navigate", async () => {
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
    expect(screen.queryByText(/review page/i)).not.toBeInTheDocument();
  });

  it("shows backend 5xx error message and does not navigate", async () => {
    global.fetch.mockResolvedValue({
      status: 500,
      ok: false,
      json: async () => ({ error: "Falló el servidor" }),
    });
    renderUpload();
    const input = screen.getByLabelText(/seleccionar archivo/i);
    const file = makeFile("pedido.pdf", 1024, "application/pdf");
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/falló el servidor/i);
    });
    expect(screen.queryByText(/review page/i)).not.toBeInTheDocument();
  });

  it("falls back to generic Spanish message on 5xx without error field", async () => {
    global.fetch.mockResolvedValue({
      status: 500,
      ok: false,
      json: async () => ({}),
    });
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

  it("shows connection error on network failure and does not navigate", async () => {
    global.fetch.mockRejectedValue(new Error("network down"));
    renderUpload();
    const input = screen.getByLabelText(/seleccionar archivo/i);
    const file = makeFile("pedido.pdf", 1024, "application/pdf");
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/error de conexión/i);
    });
    expect(screen.queryByText(/review page/i)).not.toBeInTheDocument();
  });

  it("redirects to /login with explanatory message on 401", async () => {
    global.fetch.mockResolvedValue({
      status: 401,
      ok: false,
      json: async () => ({ error: "no autenticado" }),
    });
    renderUpload();
    const input = screen.getByLabelText(/seleccionar archivo/i);
    const file = makeFile("pedido.pdf", 1024, "application/pdf");
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => {
      expect(screen.getByText(/login page/i)).toHaveTextContent(
        /tu sesión expiró/i,
      );
    });
  });
});
