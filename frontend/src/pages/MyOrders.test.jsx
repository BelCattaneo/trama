import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../contexts/AuthContext";
import MyOrders, { computeStats } from "./MyOrders";

const USER = {
  user: { id: "u", email: "demo@example.com", full_name: "Demo" },
  node: { id: "n", display_name: "Cooperativa Demo", role: "consumer" },
};

const OPERATIONS = [
  {
    id: "op-1",
    operation_date: "2026-03-17",
    line_count: 5,
    kind: "order",
    confirmed_at: "2026-03-17T18:00:00Z",
    source_filename: "pedido-marzo.xlsx",
  },
  {
    id: "op-2",
    operation_date: "2026-03-10",
    line_count: 8,
    kind: "order",
    confirmed_at: "2026-03-10T12:00:00Z",
    source_filename: "lista-frutas.csv",
  },
  {
    id: "op-3",
    operation_date: "2026-03-01",
    line_count: 3,
    kind: "order",
    confirmed_at: "2026-03-01T09:00:00Z",
    source_filename: null,
  },
];

function renderPage(initialEntries = ["/my-orders"]) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <AuthProvider initialUser={USER}>
        <Routes>
          <Route path="/my-orders" element={<MyOrders />} />
          <Route path="/my-orders/:id" element={<div>detail page</div>} />
          <Route path="/login" element={<div>login page</div>} />
          <Route path="/upload" element={<div>upload page</div>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

function mockOperationsResponse(operations) {
  global.fetch.mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({ items: operations, total: operations.length }),
  });
}

beforeEach(() => {
  vi.spyOn(global, "fetch").mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("MyOrders", () => {
  it("shows loading state until fetch resolves", async () => {
    let resolve;
    global.fetch.mockImplementation(
      () =>
        new Promise((res) => {
          resolve = res;
        }),
    );
    renderPage();
    expect(screen.getByRole("status")).toHaveTextContent(/cargando/i);
    await act(async () => {
      resolve({
        ok: true,
        status: 200,
        json: async () => ({ items: [], total: 0 }),
      });
    });
    await waitFor(() => {
      expect(screen.queryByRole("status")).not.toBeInTheDocument();
    });
  });

  it("renders rows sorted by confirmed_at DESC as provided by the API", async () => {
    mockOperationsResponse(OPERATIONS);
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("row-op-1")).toBeInTheDocument();
    });
    const tbody = screen.getByTestId("row-op-1").parentElement;
    const orderedIds = Array.from(tbody.children).map(
      (row) => row.dataset.testid,
    );
    expect(orderedIds).toEqual(["row-op-1", "row-op-2", "row-op-3"]);
    const firstRow = screen.getByTestId("row-op-1");
    expect(within(firstRow).getByText("5")).toBeInTheDocument();
    expect(within(firstRow).getAllByText(/pedido/i).length).toBeGreaterThan(0);
  });

  it("calls /api/operations?limit=200 on mount", async () => {
    mockOperationsResponse([]);
    renderPage();
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalled();
    });
    const [url] = global.fetch.mock.calls[0];
    expect(url).toBe("/api/operations?limit=200");
  });

  it("renders empty state with Spanish message + CTA", async () => {
    mockOperationsResponse([]);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/todavía no tenés pedidos/i)).toBeInTheDocument();
    });
    expect(
      screen.getByRole("link", { name: /subir mi primer pedido/i }),
    ).toBeInTheDocument();
  });

  it("shows the backend error message in an alert when the request fails", async () => {
    global.fetch.mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({ error: "algo se rompió" }),
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/algo se rompió/i);
    });
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("applies highlighted-row class on matching ?highlight= and removes it after 3s", async () => {
    mockOperationsResponse(OPERATIONS);
    renderPage(["/my-orders?highlight=op-2"]);
    await waitFor(() => {
      expect(screen.getByTestId("row-op-2")).toBeInTheDocument();
    });
    expect(screen.getByTestId("row-op-2").className).toMatch(/highlighted-row/);
    await waitFor(
      () => {
        expect(screen.getByTestId("row-op-2").className).not.toMatch(
          /highlighted-row/,
        );
      },
      { timeout: 4000 },
    );
  });

  it("does not error when ?highlight= does not match any row", async () => {
    mockOperationsResponse(OPERATIONS);
    renderPage(["/my-orders?highlight=does-not-exist"]);
    await waitFor(() => {
      expect(screen.getByTestId("row-op-1")).toBeInTheDocument();
    });
    expect(screen.getByTestId("row-op-1").className).not.toMatch(
      /highlighted-row/,
    );
    expect(screen.getByTestId("row-op-2").className).not.toMatch(
      /highlighted-row/,
    );
    expect(screen.getByTestId("row-op-3").className).not.toMatch(
      /highlighted-row/,
    );
  });

  it("navigates to /my-orders/:id when clicking 'ver detalle'", async () => {
    mockOperationsResponse(OPERATIONS);
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("row-op-1")).toBeInTheDocument();
    });
    const detailLinks = screen.getAllByRole("link", { name: /ver detalle/i });
    fireEvent.click(detailLinks[0]);
    expect(screen.getByText(/detail page/i)).toBeInTheDocument();
  });

  it("redirects to /login on 401", async () => {
    global.fetch.mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ error: "no autenticado" }),
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/login page/i)).toBeInTheDocument();
    });
  });

  it("aborts the fetch if unmounted before it resolves", async () => {
    let abortSignal;
    global.fetch.mockImplementation((_url, init) => {
      abortSignal = init.signal;
      return new Promise(() => {});
    });
    const { unmount } = renderPage();
    unmount();
    expect(abortSignal.aborted).toBe(true);
  });
});

describe("computeStats", () => {
  it("returns zeroes for an empty list", () => {
    expect(computeStats([])).toEqual({
      confirmed: 0,
      totalLines: 0,
      latestDate: null,
    });
  });

  it("counts operations and sums line_count", () => {
    const stats = computeStats([
      { operation_date: "2026-03-17", line_count: 5 },
      { operation_date: "2026-03-10", line_count: 8 },
      { operation_date: "2026-03-01", line_count: 3 },
    ]);
    expect(stats.confirmed).toBe(3);
    expect(stats.totalLines).toBe(16);
  });

  it("treats missing line_count as 0", () => {
    const stats = computeStats([
      { operation_date: "2026-03-17", line_count: 5 },
      { operation_date: "2026-03-10" },
      { operation_date: "2026-03-01", line_count: null },
    ]);
    expect(stats.totalLines).toBe(5);
  });

  it("picks the most recent operation_date lexically (ISO YYYY-MM-DD)", () => {
    const stats = computeStats([
      { operation_date: "2026-03-01", line_count: 1 },
      { operation_date: "2026-03-17", line_count: 1 },
      { operation_date: "2026-03-10", line_count: 1 },
    ]);
    expect(stats.latestDate).toBe("2026-03-17");
  });

  it("ignores operations with null operation_date when picking latest", () => {
    const stats = computeStats([
      { operation_date: null, line_count: 1 },
      { operation_date: "2026-03-17", line_count: 1 },
    ]);
    expect(stats.latestDate).toBe("2026-03-17");
  });

  it("returns null latestDate if all dates are missing", () => {
    const stats = computeStats([
      { operation_date: null, line_count: 1 },
      { line_count: 2 },
    ]);
    expect(stats.latestDate).toBe(null);
  });
});
