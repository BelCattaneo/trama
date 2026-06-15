import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../contexts/AuthContext";
import OrderDetail from "./OrderDetail";

const USER = {
  user: { id: "u", email: "demo@example.com", full_name: "Demo" },
  node: { id: "n", display_name: "Cooperativa Demo", role: "consumer" },
};

function makeOperation({
  id = "op-1",
  document_id = "doc-1",
  operation_date = "2026-03-17",
  lines = [
    { line_no: 1, product: "tomate", quantity: 2, unit: "kg", page: null },
    { line_no: 2, product: "lechuga", quantity: 1, unit: "unidad", page: null },
  ],
} = {}) {
  return { id, document_id, operation_date, lines };
}

function renderPage({
  fetchImpl,
  initialEntry = "/my-orders/op-1",
  extraRoutes = [],
} = {}) {
  vi.spyOn(global, "fetch").mockImplementation(fetchImpl);
  const router = createMemoryRouter(
    [
      {
        path: "/my-orders/:operation_id",
        element: (
          <AuthProvider initialUser={USER}>
            <OrderDetail />
          </AuthProvider>
        ),
      },
      {
        path: "/my-orders",
        element: (
          <AuthProvider initialUser={USER}>
            <div data-testid="my-orders">my orders</div>
          </AuthProvider>
        ),
      },
      {
        path: "/login",
        element: <div data-testid="login">login</div>,
      },
      ...extraRoutes,
    ],
    { initialEntries: [initialEntry] },
  );
  return { ...render(<RouterProvider router={router} />), router };
}

beforeEach(() => {
  vi.spyOn(global, "fetch").mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.resetModules();
});

describe("OrderDetail", () => {
  it("shows loading state until fetch resolves", async () => {
    let resolveFetch;
    const fetchPromise = new Promise((res) => {
      resolveFetch = res;
    });
    renderPage({ fetchImpl: () => fetchPromise });
    expect(screen.getByRole("status")).toHaveTextContent(/cargando/i);
    resolveFetch({
      ok: true,
      status: 200,
      json: async () => makeOperation(),
    });
    await waitFor(() => {
      expect(screen.queryByRole("status")).not.toBeInTheDocument();
    });
  });

  it("renders header (fecha + cantidad de líneas) and lines table on success", async () => {
    renderPage({
      fetchImpl: () =>
        Promise.resolve({
          ok: true,
          status: 200,
          json: async () => makeOperation(),
        }),
    });
    await screen.findByText("tomate");
    expect(screen.getByText("lechuga")).toBeInTheDocument();
    // Fecha header (DD MMM YYYY in Spanish, e.g. "17 mar 2026")
    expect(screen.getByText(/17/)).toBeInTheDocument();
    // Line count
    const meta = screen.getByText(/cantidad de líneas/i).closest("div");
    expect(meta).toHaveTextContent("2");
  });

  it("'volver' link navigates to /my-orders", async () => {
    const { router } = renderPage({
      fetchImpl: () =>
        Promise.resolve({
          ok: true,
          status: 200,
          json: async () => makeOperation(),
        }),
    });
    const back = await screen.findByRole("link", { name: /volver/i });
    fireEvent.click(back);
    await waitFor(() => {
      expect(screen.getByTestId("my-orders")).toBeInTheDocument();
    });
    expect(router.state.location.pathname).toBe("/my-orders");
  });

  it("'ver archivo original' opens /api/documents/<doc_id>/file in a new tab", async () => {
    renderPage({
      fetchImpl: () =>
        Promise.resolve({
          ok: true,
          status: 200,
          json: async () => makeOperation({ document_id: "doc-42" }),
        }),
    });
    const link = await screen.findByRole("link", {
      name: /ver archivo original/i,
    });
    expect(link).toHaveAttribute("href", "/api/documents/doc-42/file");
    expect(link).toHaveAttribute("target", "_blank");
  });

  it("hides the Página column when all lines have page === null", async () => {
    renderPage({
      fetchImpl: () =>
        Promise.resolve({
          ok: true,
          status: 200,
          json: async () => makeOperation(),
        }),
    });
    await screen.findByText("tomate");
    expect(
      screen.queryByRole("columnheader", { name: /página/i }),
    ).not.toBeInTheDocument();
  });

  it("shows the Página column when at least one line has page !== null", async () => {
    renderPage({
      fetchImpl: () =>
        Promise.resolve({
          ok: true,
          status: 200,
          json: async () =>
            makeOperation({
              lines: [
                {
                  line_no: 1,
                  product: "tomate",
                  quantity: 2,
                  unit: "kg",
                  page: 3,
                },
                {
                  line_no: 2,
                  product: "lechuga",
                  quantity: 1,
                  unit: "unidad",
                  page: null,
                },
              ],
            }),
        }),
    });
    await screen.findByText("tomate");
    expect(
      screen.getByRole("columnheader", { name: /página/i }),
    ).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("on 404, navigates to /my-orders and passes a toast in location state", async () => {
    const { router } = renderPage({
      fetchImpl: () =>
        Promise.resolve({
          ok: false,
          status: 404,
          json: async () => ({}),
        }),
    });
    await waitFor(() => {
      expect(screen.getByTestId("my-orders")).toBeInTheDocument();
    });
    expect(router.state.location.pathname).toBe("/my-orders");
    expect(router.state.location.state).toEqual({
      toast: "pedido no encontrado",
    });
  });

  it("on 401, redirects to /login", async () => {
    const { router } = renderPage({
      fetchImpl: () =>
        Promise.resolve({
          ok: false,
          status: 401,
          json: async () => ({}),
        }),
    });
    await waitFor(() => {
      expect(screen.getByTestId("login")).toBeInTheDocument();
    });
    expect(router.state.location.pathname).toBe("/login");
  });

  it("on other errors, shows the backend error message in a toast", async () => {
    renderPage({
      fetchImpl: () =>
        Promise.resolve({
          ok: false,
          status: 500,
          json: async () => ({ error: "fallo en el servidor" }),
        }),
    });
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        /fallo en el servidor/i,
      );
    });
  });

  it("aborts the fetch when unmounted before it resolves", async () => {
    let abortSignal;
    const { unmount } = renderPage({
      fetchImpl: (_url, init) => {
        abortSignal = init.signal;
        return new Promise(() => {});
      },
    });
    unmount();
    expect(abortSignal.aborted).toBe(true);
  });

  it("downloads CSV with role-prefixed filename when the button is clicked", async () => {
    const createObjectURL = vi
      .spyOn(URL, "createObjectURL")
      .mockReturnValue("blob:fake");
    const revokeObjectURL = vi
      .spyOn(URL, "revokeObjectURL")
      .mockImplementation(() => {});
    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => {});

    renderPage({
      fetchImpl: () =>
        Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            ...makeOperation({
              id: "a1b2c3d4e5f6",
              operation_date: "2026-06-15",
            }),
            kind: "offer",
          }),
        }),
    });
    const button = await screen.findByRole("button", {
      name: /descargar csv/i,
    });
    fireEvent.click(button);

    expect(createObjectURL).toHaveBeenCalledTimes(1);
    const [blob] = createObjectURL.mock.calls[0];
    expect(blob).toBeInstanceOf(Blob);
    expect(blob.type).toMatch(/text\/csv/);

    const anchor = clickSpy.mock.instances[0];
    expect(anchor.download).toBe("oferta_2026-06-15_a1b2c3d4.csv");
    expect(anchor.href).toBe("blob:fake");
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:fake");
  });

  it("disables the CSV button when there are no lines", async () => {
    renderPage({
      fetchImpl: () =>
        Promise.resolve({
          ok: true,
          status: 200,
          json: async () => makeOperation({ lines: [] }),
        }),
    });
    const button = await screen.findByRole("button", {
      name: /descargar csv/i,
    });
    expect(button).toBeDisabled();
  });
});
