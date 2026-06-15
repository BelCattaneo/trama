import "./Input.css";

export default function Input({ label, id, error, ...inputProps }) {
  const errorId = error ? `${id}-error` : undefined;
  return (
    <div className="input-field">
      <label htmlFor={id} className="input-field__label">
        {label}
      </label>
      <input
        id={id}
        className="input-field__box"
        aria-invalid={error ? true : undefined}
        aria-describedby={errorId}
        {...inputProps}
      />
      {error && (
        <p id={errorId} className="input-field__error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
