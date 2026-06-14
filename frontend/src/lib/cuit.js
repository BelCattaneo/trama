const FORMAT = /^\d{2}-?\d{8}-?\d{1}$/;

export function isValidCuitFormat(value) {
  return FORMAT.test(value);
}

export function formatCuit(value) {
  const digits = value.replace(/\D/g, "").slice(0, 11);
  if (digits.length <= 2) return digits;
  if (digits.length <= 10) return `${digits.slice(0, 2)}-${digits.slice(2)}`;
  return `${digits.slice(0, 2)}-${digits.slice(2, 10)}-${digits.slice(10)}`;
}
