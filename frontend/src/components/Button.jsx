import "./Button.css";

export default function Button({
  variant = "primary",
  type = "button",
  fullWidth = false,
  loading = false,
  disabled = false,
  children,
  ...props
}) {
  const classes = ["btn", `btn--${variant}`];
  if (fullWidth) classes.push("btn--full");
  return (
    <button
      type={type}
      className={classes.join(" ")}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? "Cargando…" : children}
    </button>
  );
}
