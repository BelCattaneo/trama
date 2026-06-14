export const MAX_BYTES = 10 * 1024 * 1024;

export const ACCEPTED_EXTENSIONS = [
  ".xlsx",
  ".csv",
  ".jpg",
  ".jpeg",
  ".png",
  ".pdf",
];

const ACCEPTED_MIMES = new Set([
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "text/csv",
  "image/jpeg",
  "image/png",
  "application/pdf",
]);

function isAcceptedFile(file) {
  if (ACCEPTED_MIMES.has(file.type)) return true;
  const name = file.name.toLowerCase();
  return ACCEPTED_EXTENSIONS.some((ext) => name.endsWith(ext));
}

export function validateClientFile(file) {
  if (!isAcceptedFile(file)) {
    return {
      ok: false,
      error: "Formato no soportado. Aceptamos xlsx, csv, jpg, png o pdf.",
    };
  }
  if (file.size > MAX_BYTES) {
    return { ok: false, error: "El archivo es muy grande. Máximo 10 MB." };
  }
  return { ok: true };
}
