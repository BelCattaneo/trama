import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useReviewState } from "./useReviewState";

function makePayload() {
  return {
    lines: [
      {
        product: "tomate",
        quantity: 2,
        unit: "kg",
        raw_text: "tomate 2kg",
        page: 1,
      },
      {
        product: "zanahoria",
        quantity: 5,
        unit: "kg",
        raw_text: "zanahoria 5kg",
        page: 1,
      },
    ],
    warnings: [],
  };
}

describe("useReviewState", () => {
  it("initializes lines from payload with their original index as line_no", () => {
    const { result } = renderHook(() => useReviewState(makePayload()));
    expect(result.current.lines).toHaveLength(2);
    expect(result.current.lines[0].line_no).toBe(0);
    expect(result.current.lines[1].line_no).toBe(1);
    expect(result.current.lines[0]).not.toHaveProperty("_clientId");
  });

  it("addLine appends a line with line_no null and a unique _clientId", () => {
    const { result } = renderHook(() => useReviewState(makePayload()));
    act(() => {
      result.current.addLine();
      result.current.addLine();
    });
    const added = result.current.lines.slice(2);
    expect(added).toHaveLength(2);
    for (const line of added) {
      expect(line.line_no).toBeNull();
      expect(typeof line._clientId).toBe("string");
      expect(line.product).toBe("");
      expect(line.quantity).toBe(0);
      expect(line.unit).toBeNull();
      expect(line.raw_text).toBeNull();
      expect(line.page).toBeNull();
    }
    expect(added[0]._clientId).not.toBe(added[1]._clientId);
  });

  it("removeLine by line_no removes the original line", () => {
    const { result } = renderHook(() => useReviewState(makePayload()));
    act(() => {
      result.current.removeLine(0);
    });
    expect(result.current.lines).toHaveLength(1);
    expect(result.current.lines[0].line_no).toBe(1);
    expect(result.current.lines[0].product).toBe("zanahoria");
  });

  it("removeLine by _clientId removes the added line", () => {
    const { result } = renderHook(() => useReviewState(makePayload()));
    act(() => {
      result.current.addLine();
    });
    const clientId = result.current.lines[2]._clientId;
    act(() => {
      result.current.removeLine(clientId);
    });
    expect(result.current.lines).toHaveLength(2);
    expect(result.current.lines.every((line) => line.line_no !== null)).toBe(
      true,
    );
  });

  it("updateField updates product and reflects in lines", () => {
    const { result } = renderHook(() => useReviewState(makePayload()));
    act(() => {
      result.current.updateField(0, "product", "tomate perita");
    });
    expect(result.current.lines[0].product).toBe("tomate perita");
  });

  it("updateField on quantity parses string to number", () => {
    const { result } = renderHook(() => useReviewState(makePayload()));
    act(() => {
      result.current.updateField(0, "quantity", "3.5");
    });
    expect(result.current.lines[0].quantity).toBe(3.5);
  });

  it("updateField on quantity maps empty/NaN to 0", () => {
    const { result } = renderHook(() => useReviewState(makePayload()));
    act(() => {
      result.current.updateField(0, "quantity", "");
    });
    expect(result.current.lines[0].quantity).toBe(0);
    act(() => {
      result.current.updateField(0, "quantity", "abc");
    });
    expect(result.current.lines[0].quantity).toBe(0);
  });

  it("updateField stores unit as-is", () => {
    const { result } = renderHook(() => useReviewState(makePayload()));
    act(() => {
      result.current.updateField(0, "unit", "atado");
    });
    expect(result.current.lines[0].unit).toBe("atado");
  });

  it("getCorrections returns [] when nothing changed", () => {
    const { result } = renderHook(() => useReviewState(makePayload()));
    expect(result.current.getCorrections()).toEqual([]);
  });

  it("getCorrections returns one correction per modified field", () => {
    const { result } = renderHook(() => useReviewState(makePayload()));
    act(() => {
      result.current.updateField(0, "product", "tomate perita");
      result.current.updateField(0, "quantity", "3");
      result.current.updateField(0, "unit", "atado");
    });
    const corrections = result.current.getCorrections();
    expect(corrections).toHaveLength(3);
    expect(corrections).toEqual(
      expect.arrayContaining([
        {
          line_no: 0,
          field: "product",
          original_value: "tomate",
          corrected_value: "tomate perita",
        },
        {
          line_no: 0,
          field: "quantity",
          original_value: "2",
          corrected_value: "3",
        },
        {
          line_no: 0,
          field: "unit",
          original_value: "kg",
          corrected_value: "atado",
        },
      ]),
    );
  });

  it("getCorrections does not emit a correction when the value is unchanged", () => {
    const { result } = renderHook(() => useReviewState(makePayload()));
    act(() => {
      result.current.updateField(0, "product", "tomate");
    });
    expect(result.current.getCorrections()).toEqual([]);
  });

  it("getCorrections emits line_added with JSON without _clientId", () => {
    const { result } = renderHook(() => useReviewState(makePayload()));
    act(() => {
      result.current.addLine();
    });
    const clientId = result.current.lines[2]._clientId;
    act(() => {
      result.current.updateField(clientId, "product", "lechuga");
      result.current.updateField(clientId, "quantity", "4");
      result.current.updateField(clientId, "unit", "atado");
    });
    const corrections = result.current.getCorrections();
    expect(corrections).toHaveLength(1);
    const [added] = corrections;
    expect(added.line_no).toBeNull();
    expect(added.field).toBe("line_added");
    expect(added.original_value).toBeNull();
    const parsed = JSON.parse(added.corrected_value);
    expect(parsed).not.toHaveProperty("_clientId");
    expect(parsed.product).toBe("lechuga");
    expect(parsed.quantity).toBe(4);
    expect(parsed.unit).toBe("atado");
    expect(parsed.page).toBeNull();
  });

  it("getCorrections emits line_removed with original JSON for deleted lines", () => {
    const { result } = renderHook(() => useReviewState(makePayload()));
    act(() => {
      result.current.removeLine(1);
    });
    const corrections = result.current.getCorrections();
    expect(corrections).toHaveLength(1);
    const [removed] = corrections;
    expect(removed.line_no).toBe(1);
    expect(removed.field).toBe("line_removed");
    expect(removed.corrected_value).toBeNull();
    const parsed = JSON.parse(removed.original_value);
    expect(parsed).not.toHaveProperty("_clientId");
    expect(parsed.product).toBe("zanahoria");
    expect(parsed.quantity).toBe(5);
    expect(parsed.unit).toBe("kg");
    expect(parsed.page).toBe(1);
  });

  it("getFinalPayload returns ParsePayload shape without _clientId and without removed lines", () => {
    const { result } = renderHook(() => useReviewState(makePayload()));
    act(() => {
      result.current.removeLine(0);
      result.current.addLine();
    });
    const clientId = result.current.lines[1]._clientId;
    act(() => {
      result.current.updateField(clientId, "product", "lechuga");
    });
    const payload = result.current.getFinalPayload();
    expect(payload.warnings).toEqual([]);
    expect(payload.lines).toHaveLength(2);
    for (const line of payload.lines) {
      expect(line).not.toHaveProperty("_clientId");
    }
    const original = payload.lines.find((line) => line.line_no === 1);
    expect(original.product).toBe("zanahoria");
    expect(original.page).toBe(1);
    const added = payload.lines.find((line) => line.line_no === null);
    expect(added.product).toBe("lechuga");
    expect(added.page).toBeNull();
  });
});
