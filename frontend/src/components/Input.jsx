import "./Input.css";

export default function Input({ label, id, error, ...inputProps }) {
  return (
    <div className="input-field">
      <label htmlFor={id} className="input-field__label">
        {label}
      </label>
      <input id={id} className="input-field__box" {...inputProps} />
      {error && <p className="input-field__error">{error}</p>}
    </div>
  );
}
