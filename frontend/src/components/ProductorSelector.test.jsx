import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ProductorSelector from "./ProductorSelector";

const MATCHED_NODE = {
  id: "node-123",
  display_name: "Cooperativa Nogal",
  cuit: "30-71234567-1",
  role: "producer",
  zone_label: "CABA",
};

const PRODUCERS = [
  {
    id: "p1",
    display_name: "Anaranjados",
    cuit: "30-00000001-2",
    role: "producer",
  },
  { id: "p2", display_name: "Bionogal", cuit: "30-00000002-0", role: "both" },
];

function mockProducersFetch(producers = PRODUCERS) {
  global.fetch.mockImplementation(async (url) => {
    if (url.includes("/api/producers")) {
      return {
        ok: true,
        status: 200,
        json: async () => ({ producers }),
      };
    }
    return { ok: false, status: 404, json: async () => ({}) };
  });
}

beforeEach(() => {
  vi.spyOn(global, "fetch").mockReset();
  mockProducersFetch();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("ProductorSelector — variant A (matched)", () => {
  it("renders the matched producer with the green badge and Cambiar link", async () => {
    render(
      <ProductorSelector
        detection={{ cuit: MATCHED_NODE.cuit, matched_node: MATCHED_NODE }}
        value={MATCHED_NODE.id}
        onChange={() => {}}
      />,
    );
    expect(screen.getByText(/Cooperativa Nogal/i)).toBeInTheDocument();
    expect(screen.getByText(/CUIT 30-71234567-1/i)).toBeInTheDocument();
    expect(screen.getByText(/Detectado del documento/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /cambiar/i }),
    ).toBeInTheDocument();
  });

  it("clicking Cambiar shows the combobox search input", async () => {
    render(
      <ProductorSelector
        detection={{ cuit: MATCHED_NODE.cuit, matched_node: MATCHED_NODE }}
        value={MATCHED_NODE.id}
        onChange={() => {}}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /cambiar/i }));
    await waitFor(() =>
      expect(screen.getByLabelText(/buscar productorx/i)).toBeInTheDocument(),
    );
  });
});

describe("ProductorSelector — variant B (CUIT detected, no match)", () => {
  it("renders the warning with the raw CUIT and the Agregar este productor button", () => {
    render(
      <ProductorSelector
        detection={{ cuit: "30-99999999-9", matched_node: null }}
        value={null}
        onChange={() => {}}
      />,
    );
    expect(
      screen.getByText(
        /El CUIT 30-99999999-9 fue detectado en el archivo pero no está registrado en trama/i,
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /agregar este productor/i }),
    ).toBeInTheDocument();
  });
});

describe("ProductorSelector — variant C (no detection)", () => {
  it("renders the combobox without warning", () => {
    render(
      <ProductorSelector detection={null} value={null} onChange={() => {}} />,
    );
    expect(screen.getByLabelText(/buscar productorx/i)).toBeInTheDocument();
    expect(screen.queryByText(/no está registrado/i)).not.toBeInTheDocument();
  });

  it("selecting a node fires onChange with the node id", async () => {
    const onChange = vi.fn();
    render(
      <ProductorSelector detection={null} value={null} onChange={onChange} />,
    );
    const input = screen.getByLabelText(/buscar productorx/i);
    fireEvent.focus(input);
    await waitFor(() =>
      expect(screen.getByText(/Anaranjados/i)).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByText(/Bionogal/i));
    expect(onChange).toHaveBeenCalledWith("p2");
  });

  it("dropdown has an 'Agregar nuevo productor' row", async () => {
    render(
      <ProductorSelector detection={null} value={null} onChange={() => {}} />,
    );
    const input = screen.getByLabelText(/buscar productorx/i);
    fireEvent.focus(input);
    await waitFor(() =>
      expect(
        screen.getByText(/Agregar nuevo productor/i),
      ).toBeInTheDocument(),
    );
  });
});

describe("ProductorSelector — modal", () => {
  it("opens, submits successfully, calls onChange with created id, and closes", async () => {
    const createdNode = {
      id: "new-node-id",
      display_name: "Nueva Coop",
      cuit: "30-99999999-9",
      role: "producer",
    };
    global.fetch.mockImplementation(async (url, init) => {
      if (url.includes("/api/producers")) {
        return { ok: true, status: 200, json: async () => ({ producers: [] }) };
      }
      if (url.includes("/api/nodes") && init?.method === "POST") {
        return { ok: true, status: 201, json: async () => createdNode };
      }
      return { ok: false, status: 404, json: async () => ({}) };
    });
    const onChange = vi.fn();
    render(
      <ProductorSelector
        detection={{ cuit: "30-99999999-9", matched_node: null }}
        value={null}
        onChange={onChange}
      />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: /agregar este productor/i }),
    );
    await waitFor(() =>
      expect(
        screen.getByRole("dialog", { name: /agregar productorx/i }),
      ).toBeInTheDocument(),
    );
    fireEvent.change(screen.getByLabelText(/CUIT \(opcional\)/i), {
      target: { value: "30-99999999-9" },
    });
    fireEvent.change(screen.getByLabelText(/nombre/i), {
      target: { value: "Nueva Coop" },
    });
    fireEvent.change(screen.getByLabelText(/dirección/i), {
      target: { value: "Calle 1" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^agregar$/i }));
    await waitFor(() => expect(onChange).toHaveBeenCalledWith("new-node-id"));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("shows toast on 409 duplicate CUIT", async () => {
    global.fetch.mockImplementation(async (url) => {
      if (url.includes("/api/producers")) {
        return { ok: true, status: 200, json: async () => ({ producers: [] }) };
      }
      if (url.includes("/api/nodes")) {
        return {
          ok: false,
          status: 409,
          json: async () => ({ error: "CUIT ya registrado" }),
        };
      }
      return { ok: false, status: 404, json: async () => ({}) };
    });
    render(
      <ProductorSelector
        detection={{ cuit: "30-99999999-9", matched_node: null }}
        value={null}
        onChange={() => {}}
      />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: /agregar este productor/i }),
    );
    await waitFor(() => screen.getByRole("dialog"));
    fireEvent.change(screen.getByLabelText(/nombre/i), {
      target: { value: "Dup" },
    });
    fireEvent.change(screen.getByLabelText(/dirección/i), {
      target: { value: "Calle 1" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^agregar$/i }));
    await waitFor(() =>
      expect(
        screen.getByText(/este CUIT ya está registrado/i),
      ).toBeInTheDocument(),
    );
  });

  it("Esc closes the modal", async () => {
    render(
      <ProductorSelector
        detection={{ cuit: "30-99999999-9", matched_node: null }}
        value={null}
        onChange={() => {}}
      />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: /agregar este productor/i }),
    );
    await waitFor(() => screen.getByRole("dialog"));
    fireEvent.keyDown(document, { key: "Escape" });
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
  });
});
