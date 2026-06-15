import { useCallback, useMemo, useState } from "react";

function attachLineNo(payloadLines) {
  return payloadLines.map((line, index) => ({
    line_no: index,
    product: line.product,
    quantity: line.quantity,
    unit: line.unit ?? null,
    raw_text: line.raw_text ?? null,
    page: line.page ?? null,
  }));
}

function stripClientId(line) {
  return {
    line_no: line.line_no,
    product: line.product,
    quantity: line.quantity,
    unit: line.unit,
    raw_text: line.raw_text,
    page: line.page,
  };
}

function isOriginal(line) {
  return line.line_no !== null;
}

function matches(line, identifier) {
  return isOriginal(line)
    ? line.line_no === identifier
    : line._clientId === identifier;
}

export function useReviewState(initialPayload) {
  const originalLines = useMemo(
    () => attachLineNo(initialPayload.lines),
    [initialPayload],
  );
  const [lines, setLines] = useState(originalLines);

  const addLine = useCallback(() => {
    setLines((current) => [
      ...current,
      {
        line_no: null,
        _clientId: crypto.randomUUID(),
        product: "",
        quantity: 0,
        unit: null,
        raw_text: null,
        page: null,
      },
    ]);
  }, []);

  const removeLine = useCallback((identifier) => {
    setLines((current) => current.filter((line) => !matches(line, identifier)));
  }, []);

  const updateField = useCallback((identifier, field, value) => {
    setLines((current) =>
      current.map((line) => {
        if (!matches(line, identifier)) return line;
        if (field === "quantity") {
          const parsed = parseFloat(value);
          return { ...line, quantity: Number.isNaN(parsed) ? 0 : parsed };
        }
        return { ...line, [field]: value };
      }),
    );
  }, []);

  const getCorrections = useCallback(() => {
    const originalByLineNo = new Map(
      originalLines.map((line) => [line.line_no, line]),
    );
    const survivingLineNos = new Set(
      lines.filter(isOriginal).map((line) => line.line_no),
    );
    const corrections = [];

    for (const line of lines) {
      if (isOriginal(line)) {
        const original = originalByLineNo.get(line.line_no);
        for (const field of ["product", "quantity", "unit"]) {
          if (line[field] !== original[field]) {
            corrections.push({
              line_no: line.line_no,
              field,
              original_value: String(original[field]),
              corrected_value: String(line[field]),
            });
          }
        }
      } else {
        corrections.push({
          line_no: null,
          field: "line_added",
          original_value: null,
          corrected_value: JSON.stringify(stripClientId(line)),
        });
      }
    }

    for (const original of originalLines) {
      if (!survivingLineNos.has(original.line_no)) {
        corrections.push({
          line_no: original.line_no,
          field: "line_removed",
          original_value: JSON.stringify(original),
          corrected_value: null,
        });
      }
    }

    return corrections;
  }, [lines, originalLines]);

  const getFinalPayload = useCallback(
    () => ({
      lines: lines.map(stripClientId),
      warnings: [],
    }),
    [lines],
  );

  return {
    lines,
    addLine,
    removeLine,
    updateField,
    getCorrections,
    getFinalPayload,
  };
}
