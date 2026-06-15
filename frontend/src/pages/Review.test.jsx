import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../contexts/AuthContext";
import Review from "./Review";

const DEFAULT_USER = {
  user: { id: "u", email: "demo@example.com", full_name: "Demo" },
  node: {
    id: "n",
    display_name: "Cooperativa Demo",
    role: "consumer",
  },
};

function makeReviewBody({
  mime = "image/jpeg",
  filename = "doc.jpg",
  confidence = 1.0,
  payloadLines = [{ product: "tomate", quantity: 2, unit: "kg", page: 1 }],
  warnings = [],
  isWinner = false,
  errorMessage = null,
} = {}) {
  return {
    document: {
      id: "doc-1",
      original_filename: filename,
      mime_type: mime,
      size_bytes: 1024,
      content_hash: "x".repeat(64),
      uploaded_at: "2026-01-01T00:00:00Z",
    },
    parse_attempt: {
      id: "att-1",
      strategy: "deterministic",
      confidence,
      payload: { lines: payloadLines, warnings },
      prompt_version: null,
      error_message: errorMessage,
      is_winner: isWinner,
      created_at: "2026-01-01T00:00:00Z",
    },
  };
}

function renderReview({ body = makeReviewBody(), extraRoutes = [] } = {}) {
  vi.spyOn(global, "fetch").mockImplementation((url) => {
    if (typeof url === "string" && url.includes("/review")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => body,
      });
    }
    return Promise.resolve({ ok: true, status: 200, json: async () => ({}) });
  });
  const router = createMemoryRouter(
    [
      {
        path: "/review/:document_id",
        element: (
          <AuthProvider initialUser={DEFAULT_USER}>
            <Review />
          </AuthProvider>
        ),
      },
      {
        path: "/my-orders",
        element: (
          <AuthProvider initialUser={DEFAULT_USER}>
            <div data-testid="my-orders">my orders</div>
          </AuthProvider>
        ),
      },
      ...extraRoutes,
    ],
    { initialEntries: ["/review/doc-1"] },
  );
  return render(<RouterProvider router={router} />);
}

beforeEach(() => {
  vi.spyOn(global, "fetch").mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.resetModules();
});

describe("Review", () => {
  it("renders an <img> preview for jpeg", async () => {
    renderReview({ body: makeReviewBody({ mime: "image/jpeg" }) });
    const img = await screen.findByAltText("doc.jpg");
    expect(img).toHaveAttribute("src", "/api/documents/doc-1/file");
  });

  it("renders an <img> preview for png", async () => {
    renderReview({
      body: makeReviewBody({ mime: "image/png", filename: "doc.png" }),
    });
    const img = await screen.findByAltText("doc.png");
    expect(img.tagName).toBe("IMG");
  });

  it("renders the spreadsheet fallback with download link", async () => {
    renderReview({
      body: makeReviewBody({
        mime: "text/csv",
        filename: "p.csv",
        payloadLines: [{ product: "tomate", quantity: 1, unit: "kg" }],
      }),
    });
    const link = await screen.findByRole("link", {
      name: /descargar original/i,
    });
    expect(link).toHaveAttribute("href", "/api/documents/doc-1/file");
  });

  it("triggers HEIC decode and renders an <img> when decode resolves", async () => {
    vi.doMock("heic2any", () => ({
      default: vi.fn(async () => new Blob(["jpeg"], { type: "image/jpeg" })),
    }));
    const objectUrl = "blob:fake-url";
    if (!URL.createObjectURL) URL.createObjectURL = () => objectUrl;
    if (!URL.revokeObjectURL) URL.revokeObjectURL = () => {};
    const createSpy = vi
      .spyOn(URL, "createObjectURL")
      .mockReturnValue(objectUrl);
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
    vi.spyOn(global, "fetch").mockImplementation((url) => {
      if (typeof url === "string" && url.includes("/review")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () =>
            makeReviewBody({ mime: "image/heic", filename: "doc.heic" }),
        });
      }
      if (typeof url === "string" && url.includes("/file")) {
        return Promise.resolve({
          ok: true,
          blob: async () => new Blob(["heic"], { type: "image/heic" }),
        });
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) });
    });
    const router = createMemoryRouter(
      [
        {
          path: "/review/:document_id",
          element: (
            <AuthProvider initialUser={DEFAULT_USER}>
              <Review />
            </AuthProvider>
          ),
        },
      ],
      { initialEntries: ["/review/doc-1"] },
    );
    render(<RouterProvider router={router} />);
    const img = await screen.findByAltText("doc.heic", {}, { timeout: 3000 });
    expect(img).toHaveAttribute("src", objectUrl);
    expect(createSpy).toHaveBeenCalled();
    vi.doUnmock("heic2any");
  });

  it("triggers PDF render via pdfjs-dist", async () => {
    const renderMock = vi.fn(() => ({ promise: Promise.resolve() }));
    const getPageMock = vi.fn(async () => ({
      getViewport: () => ({ width: 100, height: 100 }),
      render: renderMock,
    }));
    vi.doMock("pdfjs-dist", () => ({
      GlobalWorkerOptions: { workerSrc: "" },
      getDocument: vi.fn(() => ({
        promise: Promise.resolve({
          numPages: 1,
          getPage: getPageMock,
        }),
      })),
    }));
    vi.doMock("pdfjs-dist/build/pdf.worker.mjs?url", () => ({
      default: "fake-worker-url",
    }));
    vi.spyOn(global, "fetch").mockImplementation((url) => {
      if (typeof url === "string" && url.includes("/review")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () =>
            makeReviewBody({ mime: "application/pdf", filename: "doc.pdf" }),
        });
      }
      if (typeof url === "string" && url.includes("/file")) {
        return Promise.resolve({
          ok: true,
          arrayBuffer: async () => new ArrayBuffer(8),
        });
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) });
    });
    const router = createMemoryRouter(
      [
        {
          path: "/review/:document_id",
          element: (
            <AuthProvider initialUser={DEFAULT_USER}>
              <Review />
            </AuthProvider>
          ),
        },
      ],
      { initialEntries: ["/review/doc-1"] },
    );
    render(<RouterProvider router={router} />);
    await waitFor(() => expect(getPageMock).toHaveBeenCalledWith(1));
    await waitFor(() => expect(renderMock).toHaveBeenCalled());
    vi.doUnmock("pdfjs-dist");
    vi.doUnmock("pdfjs-dist/build/pdf.worker.mjs?url");
  });

  it("renders editable inputs for each line and updates state on change", async () => {
    renderReview({
      body: makeReviewBody({
        payloadLines: [
          { product: "tomate", quantity: 2, unit: "kg", page: 1 },
          { product: "zanahoria", quantity: 5, unit: "kg", page: 1 },
        ],
      }),
    });
    await screen.findByDisplayValue("tomate");
    const productInput = screen.getByDisplayValue("tomate");
    fireEvent.change(productInput, { target: { value: "tomate perita" } });
    expect(screen.getByDisplayValue("tomate perita")).toBeInTheDocument();
  });

  it("addLine and removeLine work via the buttons", async () => {
    renderReview({
      body: makeReviewBody({
        payloadLines: [{ product: "tomate", quantity: 2, unit: "kg", page: 1 }],
      }),
    });
    await screen.findByDisplayValue("tomate");
    fireEvent.click(screen.getByRole("button", { name: /agregar línea/i }));
    expect(screen.getAllByLabelText(/producto/i)).toHaveLength(2);
    const removeButtons = screen.getAllByRole("button", {
      name: /eliminar línea/i,
    });
    fireEvent.click(removeButtons[0]);
    expect(screen.getAllByLabelText(/producto/i)).toHaveLength(1);
  });

  it("highlights unreadable product lines yellow with the placeholder", async () => {
    renderReview({
      body: makeReviewBody({
        confidence: 0.4,
        payloadLines: [
          { product: "unreadable", quantity: 2, unit: "kg", page: 1 },
        ],
      }),
    });
    const productInput = await screen.findByPlaceholderText(/completar acá/i);
    expect(productInput).toBeInTheDocument();
    const lineRow = productInput.closest("li");
    expect(lineRow).toHaveAttribute("data-warn", "true");
  });

  it("disables confirm when a product is unreadable, enables once corrected", async () => {
    renderReview({
      body: makeReviewBody({
        payloadLines: [
          { product: "unreadable", quantity: 2, unit: "kg", page: 1 },
        ],
      }),
    });
    const confirm = await screen.findByRole("button", { name: /confirmar/i });
    expect(confirm).toBeDisabled();
    const productInput = screen.getByPlaceholderText(/completar acá/i);
    fireEvent.change(productInput, { target: { value: "tomate" } });
    expect(confirm).not.toBeDisabled();
  });

  it("disables confirm when lines is empty", async () => {
    renderReview({
      body: makeReviewBody({
        payloadLines: [{ product: "tomate", quantity: 2, unit: "kg", page: 1 }],
      }),
    });
    const removeBtn = await screen.findByRole("button", {
      name: /eliminar línea/i,
    });
    fireEvent.click(removeBtn);
    expect(screen.getByRole("button", { name: /confirmar/i })).toBeDisabled();
  });

  it("filters lines and warnings by active page on PDF documents", async () => {
    vi.doMock("pdfjs-dist", () => ({
      GlobalWorkerOptions: { workerSrc: "" },
      getDocument: vi.fn(() => ({
        promise: Promise.resolve({
          numPages: 2,
          getPage: async () => ({
            getViewport: () => ({ width: 10, height: 10 }),
            render: () => ({ promise: Promise.resolve() }),
          }),
        }),
      })),
    }));
    vi.doMock("pdfjs-dist/build/pdf.worker.mjs?url", () => ({
      default: "fake-worker-url",
    }));
    vi.spyOn(global, "fetch").mockImplementation((url) => {
      if (typeof url === "string" && url.includes("/review")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () =>
            makeReviewBody({
              mime: "application/pdf",
              payloadLines: [
                { product: "tomate", quantity: 2, unit: "kg", page: 1 },
                { product: "zanahoria", quantity: 5, unit: "kg", page: 2 },
              ],
              warnings: ["[p1] revisar tomate", "[p2] revisar zanahoria"],
              confidence: 0.4,
            }),
        });
      }
      return Promise.resolve({
        ok: true,
        arrayBuffer: async () => new ArrayBuffer(8),
        json: async () => ({}),
      });
    });
    const router = createMemoryRouter(
      [
        {
          path: "/review/:document_id",
          element: (
            <AuthProvider initialUser={DEFAULT_USER}>
              <Review />
            </AuthProvider>
          ),
        },
      ],
      { initialEntries: ["/review/doc-1"] },
    );
    render(<RouterProvider router={router} />);
    await screen.findByDisplayValue("tomate");
    expect(screen.queryByDisplayValue("zanahoria")).not.toBeInTheDocument();
    expect(screen.getByText(/\[p1\] revisar tomate/i)).toBeInTheDocument();
    expect(
      screen.queryByText(/\[p2\] revisar zanahoria/i),
    ).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: /página 2/i }));
    await screen.findByDisplayValue("zanahoria");
    expect(screen.queryByDisplayValue("tomate")).not.toBeInTheDocument();
    expect(screen.getByText(/\[p2\] revisar zanahoria/i)).toBeInTheDocument();
    vi.doUnmock("pdfjs-dist");
    vi.doUnmock("pdfjs-dist/build/pdf.worker.mjs?url");
  });

  it("renders is_winner document read-only and hides the confirm button", async () => {
    renderReview({
      body: makeReviewBody({
        isWinner: true,
        payloadLines: [{ product: "tomate", quantity: 2, unit: "kg", page: 1 }],
      }),
    });
    await screen.findByDisplayValue("tomate");
    expect(screen.getByDisplayValue("tomate")).toBeDisabled();
    expect(
      screen.queryByRole("button", { name: /confirmar/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText(/este documento ya fue confirmado/i),
    ).toBeInTheDocument();
  });

  it("warnings panel toggles open/closed", async () => {
    renderReview({
      body: makeReviewBody({
        confidence: 0.4,
        warnings: ["revisar tomate", "revisar zanahoria"],
      }),
    });
    const label = await screen.findByText(/^2 advertencias$/);
    expect(screen.getByText("revisar tomate")).toBeInTheDocument();
    fireEvent.click(label);
    expect(screen.queryByText("revisar tomate")).not.toBeInTheDocument();
    fireEvent.click(label);
    expect(screen.getByText("revisar tomate")).toBeInTheDocument();
  });

  it("singular warning header reads '1 advertencia'", async () => {
    renderReview({
      body: makeReviewBody({
        confidence: 0.4,
        warnings: ["revisar tomate"],
      }),
    });
    expect(await screen.findByText(/^1 advertencia$/)).toBeInTheDocument();
  });

  it("shows the low-confidence warning banner when confidence < 0.5", async () => {
    renderReview({ body: makeReviewBody({ confidence: 0.3 }) });
    expect(
      await screen.findByText(/sistema no estaba seguro/i),
    ).toBeInTheDocument();
  });

  it("shows the zero-confidence error banner", async () => {
    renderReview({
      body: makeReviewBody({ confidence: 0, payloadLines: [] }),
    });
    expect(
      await screen.findByText(/no se pudo parsear automáticamente/i),
    ).toBeInTheDocument();
  });

  it("navigates to /my-orders with highlight on successful confirm", async () => {
    vi.spyOn(global, "fetch").mockImplementation((url, init) => {
      if (typeof url === "string" && url.includes("/review")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => makeReviewBody(),
        });
      }
      if (typeof url === "string" && url.includes("/confirm")) {
        expect(init.method).toBe("POST");
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ operation_id: "op-99" }),
        });
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) });
    });
    const router = createMemoryRouter(
      [
        {
          path: "/review/:document_id",
          element: (
            <AuthProvider initialUser={DEFAULT_USER}>
              <Review />
            </AuthProvider>
          ),
        },
        {
          path: "/my-orders",
          element: (
            <AuthProvider initialUser={DEFAULT_USER}>
              <div data-testid="my-orders" />
            </AuthProvider>
          ),
        },
      ],
      { initialEntries: ["/review/doc-1"] },
    );
    render(<RouterProvider router={router} />);
    const confirm = await screen.findByRole("button", { name: /confirmar/i });
    fireEvent.click(confirm);
    await waitFor(() => {
      expect(screen.getByTestId("my-orders")).toBeInTheDocument();
    });
    expect(router.state.location.search).toContain("highlight=op-99");
  });

  it("shows the backend error message in a toast on confirm failure", async () => {
    vi.spyOn(global, "fetch").mockImplementation((url) => {
      if (typeof url === "string" && url.includes("/review")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => makeReviewBody(),
        });
      }
      if (typeof url === "string" && url.includes("/confirm")) {
        return Promise.resolve({
          ok: false,
          status: 409,
          json: async () => ({ error: "ya hay un ganador" }),
        });
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) });
    });
    const router = createMemoryRouter(
      [
        {
          path: "/review/:document_id",
          element: (
            <AuthProvider initialUser={DEFAULT_USER}>
              <Review />
            </AuthProvider>
          ),
        },
      ],
      { initialEntries: ["/review/doc-1"] },
    );
    render(<RouterProvider router={router} />);
    const confirm = await screen.findByRole("button", { name: /confirmar/i });
    fireEvent.click(confirm);
    await waitFor(() => {
      expect(screen.getByText(/ya hay un ganador/i)).toBeInTheDocument();
    });
  });

  it("blocks navigation away when there are unsaved changes", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    const router = createMemoryRouter(
      [
        {
          path: "/review/:document_id",
          element: (
            <AuthProvider initialUser={DEFAULT_USER}>
              <Review />
            </AuthProvider>
          ),
        },
        {
          path: "/elsewhere",
          element: (
            <AuthProvider initialUser={DEFAULT_USER}>
              <div data-testid="elsewhere" />
            </AuthProvider>
          ),
        },
      ],
      { initialEntries: ["/review/doc-1"] },
    );
    vi.spyOn(global, "fetch").mockImplementation((url) => {
      if (typeof url === "string" && url.includes("/review")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => makeReviewBody(),
        });
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) });
    });
    render(<RouterProvider router={router} />);
    const productInput = await screen.findByDisplayValue("tomate");
    fireEvent.change(productInput, { target: { value: "tomate perita" } });
    await act(async () => {
      await router.navigate("/elsewhere");
    });
    expect(confirmSpy).toHaveBeenCalledWith(
      "¿salir sin confirmar? los cambios se perderán",
    );
    expect(screen.queryByTestId("elsewhere")).not.toBeInTheDocument();
  });
});
