import "./RolePicker.css";

const OPTIONS = [
  { value: "consumer", label: "Consumidorx" },
  { value: "producer", label: "Productorx" },
  { value: "both", label: "Ambxs" },
];

export default function RolePicker({ value, onChange, label = "Rol" }) {
  return (
    <div className="role-picker">
      <span className="role-picker__label">{label}</span>
      <div className="role-picker__group" role="radiogroup" aria-label={label}>
        {OPTIONS.map((opt) => {
          const selected = opt.value === value;
          const cls = selected
            ? "role-picker__pill role-picker__pill--selected"
            : "role-picker__pill";
          return (
            <button
              type="button"
              key={opt.value}
              role="radio"
              aria-checked={selected}
              className={cls}
              onClick={() => onChange(opt.value)}
            >
              {opt.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
