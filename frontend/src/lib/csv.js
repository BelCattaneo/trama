const BOM = "﻿";
const CSV_HEADER = "producto,cantidad,unidad";
// Excel/LibreOffice evaluate leading =+-@ \t \r as formulas. Producer-uploaded
// data flows into product names, so neutralize the lead char before escaping.
const FORMULA_LEAD = /^[=+\-@\t\r]/;

function escapeField(value) {
  let str = String(value ?? "");
  if (FORMULA_LEAD.test(str)) {
    str = `'${str}`;
  }
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
