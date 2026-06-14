const FORMAT = /^\d{2}-?\d{8}-?\d{1}$/;

export function isValidCuitFormat(value) {
  return FORMAT.test(value);
}
