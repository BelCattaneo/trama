import { useEffect, useRef, useState } from "react";
import { apiGet, apiPost } from "../lib/api";
import Button from "./Button";
import ConfidenceBadge from "./ConfidenceBadge";
import Input from "./Input";
import "./ProductorSelector.css";

const ROLE_OPTIONS = [
  { value: "producer", label: "Productorx" },
  { value: "both", label: "Ambxs" },
];

const DEBOUNCE_MS = 300;
const ADD_NEW_VALUE = "__add_new__";

export default function ProductorSelector({
  detection,
  value,
  onChange,
  onCreate,
}) {
  const [overrideMode, setOverrideMode] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [prefillCuit, setPrefillCuit] = useState("");

  const matched = detection?.matched_node ?? null;
  const detectedCuit = detection?.cuit ?? null;
  const showMatchedCard = matched && !overrideMode;

  function openModal(prefill) {
    setPrefillCuit(prefill || "");
    if (onCreate) {
      onCreate(prefill || "");
    } else {
      setModalOpen(true);
    }
  }

  function handleCreated(node) {
    setModalOpen(false);
    onChange(node.id);
    setOverrideMode(false);
  }

  return (
    <section className="productor-selector">
      <p className="productor-selector__label">PRODUCTOR DEL PEDIDO</p>

      {showMatchedCard && (
        <div className="productor-selector__matched">
          <div>
            <p className="productor-selector__matched-name">
              {matched.display_name}
            </p>
            <p className="productor-selector__matched-meta">
              CUIT {matched.cuit}
            </p>
          </div>
          <ConfidenceBadge status="confirmed" label="Detectado del documento" />
          <button
            type="button"
            className="productor-selector__change"
            onClick={() => setOverrideMode(true)}
          >
            Cambiar
          </button>
        </div>
      )}

      {!showMatchedCard && detectedCuit && !matched && (
        <p className="productor-selector__warning" role="alert">
          El CUIT {detectedCuit} no está registrado en trama.
        </p>
      )}

      {!showMatchedCard && (
        <ProducerDropdown
          value={value}
          onChange={onChange}
          onAddNew={() => openModal(detectedCuit || "")}
          extraAction={
            detectedCuit && !matched ? (
              <Button
                variant="secondary"
                onClick={() => openModal(detectedCuit)}
              >
                Agregar este productor
              </Button>
            ) : null
          }
        />
      )}

      {modalOpen && (
        <AddProductorModal
          prefillCuit={prefillCuit}
          onCancel={() => setModalOpen(false)}
          onCreated={handleCreated}
        />
      )}
    </section>
  );
}

function ProducerDropdown({ value, onChange, onAddNew, extraAction }) {
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuery(query), DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [query]);

  useEffect(() => {
    let cancelled = false;
    async function fetchProducers() {
      setLoading(true);
      setError("");
      try {
        const path = debouncedQuery
          ? `/api/producers?q=${encodeURIComponent(debouncedQuery)}`
          : "/api/producers";
        const response = await apiGet(path);
        if (cancelled) return;
        if (!response.ok) {
          setError("No pudimos cargar la lista de productorxs.");
          return;
        }
        const body = await response.json();
        setItems(body.producers || []);
      } catch {
        if (!cancelled) setError("Error de conexión.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchProducers();
    return () => {
      cancelled = true;
    };
  }, [debouncedQuery]);

  function handleSelectChange(event) {
    const selected = event.target.value;
    if (selected === ADD_NEW_VALUE) {
      onAddNew();
      event.target.value = value || "";
      return;
    }
    onChange(selected || null);
  }

  return (
    <div className="productor-selector__dropdown">
      <input
        type="search"
        className="productor-selector__search"
        placeholder="Buscar productorx por nombre o CUIT"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        aria-label="Buscar productorx"
      />
      <select
        className="productor-selector__select"
        value={value || ""}
        onChange={handleSelectChange}
        aria-label="Seleccionar productorx"
      >
        <option value="">Seleccionar productorx</option>
        {items.map((p) => (
          <option key={p.id} value={p.id}>
            {p.display_name} · {p.cuit}
          </option>
        ))}
        <option value={ADD_NEW_VALUE}>+ Agregar un productor</option>
      </select>
      {loading && (
        <p className="productor-selector__hint">Cargando productorxs…</p>
      )}
      {error && (
        <p className="productor-selector__error" role="alert">
          {error}
        </p>
      )}
      {extraAction && (
        <div className="productor-selector__extra-action">{extraAction}</div>
      )}
    </div>
  );
}

function AddProductorModal({ prefillCuit, onCancel, onCreated }) {
  const [cuit, setCuit] = useState(prefillCuit || "");
  const [displayName, setDisplayName] = useState("");
  const [address, setAddress] = useState("");
  const [role, setRole] = useState("producer");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const dialogRef = useRef(null);

  useEffect(() => {
    function onKey(e) {
      if (e.key === "Escape") onCancel();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onCancel]);

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const response = await apiPost("/api/nodes", {
        cuit,
        display_name: displayName,
        address,
        role,
      });
      if (response.status === 201) {
        const body = await response.json();
        onCreated(body);
        return;
      }
      const body = await response.json().catch(() => ({}));
      if (response.status === 409) {
        setError("Este CUIT ya está registrado en trama.");
      } else {
        setError(body.error || "No pudimos agregar al productorx.");
      }
    } catch {
      setError("Error de conexión, intentá de nuevo.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="productor-modal__backdrop"
      onClick={onCancel}
      role="presentation"
    >
      <div
        className="productor-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="productor-modal-title"
        ref={dialogRef}
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="productor-modal-title" className="productor-modal__title">
          Agregar productorx
        </h2>
        <form onSubmit={handleSubmit} className="productor-modal__form">
          <Input
            id="productor-cuit"
            label="CUIT"
            value={cuit}
            onChange={(e) => setCuit(e.target.value)}
            placeholder="20-12345678-9"
            required
          />
          <Input
            id="productor-name"
            label="Nombre o razón social"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            required
          />
          <Input
            id="productor-address"
            label="Dirección"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            required
          />
          <div className="productor-modal__role-picker">
            <span className="productor-modal__role-label">Rol</span>
            <div role="radiogroup" aria-label="Rol">
              {ROLE_OPTIONS.map((opt) => {
                const selected = opt.value === role;
                return (
                  <button
                    type="button"
                    key={opt.value}
                    role="radio"
                    aria-checked={selected}
                    className={
                      selected
                        ? "productor-modal__role productor-modal__role--selected"
                        : "productor-modal__role"
                    }
                    onClick={() => setRole(opt.value)}
                  >
                    {opt.label}
                  </button>
                );
              })}
            </div>
          </div>
          {error && (
            <p className="productor-modal__error" role="alert">
              {error}
            </p>
          )}
          <div className="productor-modal__actions">
            <Button variant="secondary" type="button" onClick={onCancel}>
              Cancelar
            </Button>
            <Button variant="primary" type="submit" loading={submitting}>
              Agregar
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
