import "./ConfidenceBadge.css";

const VARIANTS = {
  high: { className: "confidence-badge--high", label: "Confianza alta" },
  medium: { className: "confidence-badge--medium", label: "Necesita revisión" },
  low: { className: "confidence-badge--low", label: "Revisión necesaria" },
  error: {
    className: "confidence-badge--error",
    label: "No pudimos interpretar",
  },
  pending: { className: "confidence-badge--pending", label: "Sin procesar" },
  confirmed: { className: "confidence-badge--confirmed", label: "Confirmado" },
};

export function documentStatus({
  hasParseAttempt,
  hasWinner,
  latestConfidence,
  latestErrorMessage,
}) {
  if (hasWinner) return "confirmed";
  if (!hasParseAttempt) return "pending";
  if (latestErrorMessage || latestConfidence === 0) return "error";
  if (latestConfidence === null || latestConfidence === undefined)
    return "pending";
  if (latestConfidence >= 0.8) return "high";
  if (latestConfidence >= 0.5) return "medium";
  return "low";
}

export default function ConfidenceBadge({ status, label }) {
  const variant = VARIANTS[status] ?? VARIANTS.pending;
  return (
    <span className={`confidence-badge ${variant.className}`}>
      <span className="confidence-badge__dot" aria-hidden="true" />
      <span className="confidence-badge__label">{label ?? variant.label}</span>
    </span>
  );
}
