import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../contexts/AuthContext";
import MapPage from "./Map";

vi.mock("react-leaflet", () => {
  const React = require("react");
  return {
    MapContainer: ({ children }) =>
      React.createElement("div", { "data-testid": "map" }, children),
    TileLayer: () => null,
    Marker: ({ children, position }) =>
      React.createElement(
        "div",
        { "data-testid": "marker", "data-pos": position.join(",") },
        children,
      ),
    Popup: ({ children }) =>
      React.createElement("div", { "data-testid": "popup" }, children),
    useMap: () => ({
      fitBounds: () => {},
    }),
  };
});

vi.mock("leaflet", () => ({
  default: {
    divIcon: () => ({}),
    latLngBounds: () => ({}),
  },
}));

const DEFAULT_USER = {
  user: { id: "u", email: "demo@example.com" },
  node: { id: "n", display_name: "Cooperativa Demo", role: "consumer" },
};

const MOCK_NODES = [
  {
    id: "n1",
    display_name: "Coop Productor",
    role: "producer",
    latitude: -34.6,
    longitude: -58.4,
    zone_label: "CABA",
    orders_last_week: 3,
    orders_total: 12,
    top_products: ["tomate", "lechuga"],
  },
  {
    id: "n2",
    display_name: "Mercado Consumidor",
    role: "consumer",
    latitude: -33.5,
    longitude: -60.1,
    zone_label: "Rosario",
    orders_last_week: 0,
    orders_total: 0,
    top_products: [],
  },
  {
    id: "n3",
    display_name: "Coop Mixta",
    role: "both",
    latitude: -31.4,
    longitude: -64.2,
    zone_label: "Córdoba",
    orders_last_week: 1,
    orders_total: 5,
    top_products: ["miel"],
  },
];

function mockMapFetch(nodes = MOCK_NODES, status = 200) {
  global.fetch.mockImplementation(async (url) => {
    if (url.includes("/api/map")) {
      return {
        ok: status === 200,
        status,
        json: async () => ({ nodes }),
      };
    }
    return { ok: true, status: 200, json: async () => ({}) };
  });
}

function renderMap() {
  return render(
    <MemoryRouter initialEntries={["/map"]}>
      <AuthProvider initialUser={DEFAULT_USER}>
        <MapPage />
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

describe("MapPage", () => {
  it("renders loading then map with markers", async () => {
    mockMapFetch();
    renderMap();
    expect(screen.getByText(/cargando mapa/i)).toBeInTheDocument();
    await waitFor(() => screen.getByTestId("map"));
    expect(screen.getAllByTestId("marker")).toHaveLength(3);
  });

  it("shows subtitle counts: producer + both vs consumer + both", async () => {
    mockMapFetch();
    renderMap();
    await waitFor(() =>
      expect(screen.getByText(/productorxs/i)).toBeInTheDocument(),
    );
    expect(screen.getByText(/2 productorxs/i)).toBeInTheDocument();
    expect(screen.getByText(/2 consumidorxs/i)).toBeInTheDocument();
  });

  it("clicking a filter toggles markers off and on", async () => {
    mockMapFetch();
    renderMap();
    await waitFor(() =>
      expect(screen.getAllByTestId("marker")).toHaveLength(3),
    );
    fireEvent.click(screen.getByRole("button", { name: /^Productorx$/i }));
    await waitFor(() =>
      expect(screen.getAllByTestId("marker")).toHaveLength(2),
    );
    fireEvent.click(screen.getByRole("button", { name: /^Productorx$/i }));
    await waitFor(() =>
      expect(screen.getAllByTestId("marker")).toHaveLength(3),
    );
  });

  it("shows fallback when all filters are off", async () => {
    mockMapFetch();
    renderMap();
    await waitFor(() => screen.getByTestId("map"));
    fireEvent.click(screen.getByRole("button", { name: /^Productorx$/i }));
    fireEvent.click(screen.getByRole("button", { name: /^Consumidorx$/i }));
    fireEvent.click(screen.getByRole("button", { name: /^Ambxs$/i }));
    await waitFor(() =>
      expect(screen.getByText(/mostrá al menos un rol/i)).toBeInTheDocument(),
    );
  });

  it("renders popup content for a node", async () => {
    mockMapFetch();
    renderMap();
    await waitFor(() => screen.getByTestId("map"));
    const popups = screen.getAllByTestId("popup");
    expect(popups[0]).toHaveTextContent("Coop Productor");
    expect(popups[0]).toHaveTextContent(/3 pedidos esta semana/i);
    expect(popups[0]).toHaveTextContent(/12 total/i);
    expect(popups[0]).toHaveTextContent(/tomate/i);
  });

  it("renders empty state when API returns 0 nodes", async () => {
    mockMapFetch([]);
    renderMap();
    await waitFor(() =>
      expect(
        screen.getByText(/todavía no hay nodxs registradxs/i),
      ).toBeInTheDocument(),
    );
  });

  it("shows error alert on network failure", async () => {
    global.fetch.mockRejectedValue(new Error("network down"));
    renderMap();
    await waitFor(() =>
      expect(
        screen.getByText(/no pudimos cargar el mapa/i),
      ).toBeInTheDocument(),
    );
  });

  it("skips nodes with invalid coordinates and logs a warning", async () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    mockMapFetch([
      ...MOCK_NODES,
      {
        id: "bad",
        display_name: "Sin coords",
        role: "producer",
        latitude: 999,
        longitude: -58,
        orders_last_week: 0,
        orders_total: 0,
        top_products: [],
      },
    ]);
    renderMap();
    await waitFor(() =>
      expect(screen.getAllByTestId("marker")).toHaveLength(3),
    );
    expect(warn).toHaveBeenCalled();
  });
});
