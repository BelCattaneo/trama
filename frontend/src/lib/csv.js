const BOM = "﻿";
const CSV_HEADER = "producto,cantidad,unidad";

function escapeField(value) {
  const str = String(value ?? "");
  if (/[",\n\r]/.test(str)) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

export function buildOperationCsv(lines) {
  const rows = lines.map((line) =>
    [
      escapeField(line.product),
      escapeField(line.quantity),
      escapeField(line.unit ?? ""),
    ].join(","),
  );
  return `${BOM}${CSV_HEADER}\n${rows.join("\n")}\n`;
}

export function buildOperationFilename({ kind, operationDate, id }) {
  const prefix = kind === "offer" ? "oferta" : "pedido";
  const shortId = String(id).slice(0, 8);
  return `${prefix}_${operationDate}_${shortId}.csv`;
}
