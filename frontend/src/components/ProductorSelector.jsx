import { useEffect, useRef, useState } from "react";
import { Plus, Search, TriangleAlert, X } from "lucide-react";
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

export default function ProductorSelector({
  detection,
  value,
  onChange,
  onCreate,
}) {
  const [overrideMode, setOverrideMode] = useState(false);
  const [dismissedCuit, setDismissedCuit] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [prefillCuit, setPrefillCuit] = useState("");
  const [pickedNode, setPickedNode] = useState(null);

  const detectionMatched = detection?.matched_node ?? null;
  const detectedCuit = detection?.cuit ?? null;
  const matched = pickedNode ?? (overrideMode ? null : detectionMatched);
  const showMatchedCard = matched && !overrideMode;
  const showUnregisteredCard =
    !showMatchedCard && detectedCuit && !detectionMatched && !dismissedCuit;
  const isFromDetection =
    matched && detectionMatched && matched.id === detectionMatched.id;

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
    setPickedNode(node);
    onChange(node.id);
    setOverrideMode(false);
  }

  function handleComboboxPick(node) {
    setPickedNode(node);
    onChange(node.id);
    setOverrideMode(false);
  }

  function handleChangeClick() {
    setPickedNode(null);
    setOverrideMode(true);
  }

  return (
    <section className="productor-selector">
      <p className="productor-selector__label">PRODUCTOR DEL PEDIDO</p>

      {showMatchedCard && (
        <div className="productor-selector__matched">
          <div className="productor-selector__matched-info">
            <p className="productor-selector__matched-name">
              {matched.display_name}
            </p>
            {matched.cuit && (
              <p className="productor-selector__matched-meta">
                CUIT {matched.cuit}
              </p>
            )}
          </div>
          <div className="productor-selector__matched-right">
            {isFromDetection && (
              <ConfidenceBadge
                status="confirmed"
                label="Detectado del documento"
              />
            )}
            <button
              type="button"
              className="productor-selector__change"
              onClick={handleChangeClick}
            >
              Cambiar
            </button>
          </div>
        </div>
      )}

      {showUnregisteredCard && (
        <UnregisteredCuitCard
          cuit={detectedCuit}
          onAddNew={() => openModal(detectedCuit)}
          onDismiss={() => setDismissedCuit(true)}
        />
      )}

      {!showMatchedCard && !showUnregisteredCard && (
        <ProducerCombobox
          value={value}
          onPick={handleComboboxPick}
          onAddNew={() => openModal("")}
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

function UnregisteredCuitCard({ cuit, onAddNew, onDismiss }) {
  return (
    <>
      <div className="productor-selector__warning-row" role="alert">
        <TriangleAlert size={14} aria-hidden="true" />
        <span>
          El CUIT {cuit} fue detectado en el archivo pero no está registrado en
          trama
        </span>
      </div>
      <div className="productor-selector__action-row">
        <div className="productor-selector__cuit-pill">
          <span>CUIT {cuit}</span>
          <button
            type="button"
            className="productor-selector__cuit-dismiss"
            onClick={onDismiss}
            aria-label="Descartar CUIT detectado"
          >
            <X size={14} aria-hidden="true" />
          </button>
        </div>
        <button
          type="button"
          className="productor-selector__add-btn"
          onClick={onAddNew}
        >
          <Plus size={14} aria-hidden="true" />
          <span>Agregar este productor</span>
        </button>
      </div>
    </>
  );
}

function ProducerCombobox({ value, onPick, onAddNew }) {
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const containerRef = useRef(null);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuery(query), DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [query]);

  useEffect(() => {
    let cancelled = false;
    async function fetchProducers() {
      try {
        const path = debouncedQuery
          ? `/api/producers?q=${encodeURIComponent(debouncedQuery)}`
          : "/api/producers";
        const response = await apiGet(path);
        if (cancelled) return;
        if (!response.ok) return;
        const body = await response.json();
        setItems(body.producers || []);
      } catch {
        if (!cancelled) setItems([]);
      }
    }
    fetchProducers();
    return () => {
      cancelled = true;
    };
  }, [debouncedQuery]);

  useEffect(() => {
    function onClickOutside(event) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  const totalRows = items.length + 1; // +1 for "Agregar nuevo"

  function pickItem(idx) {
    if (idx === items.length) {
      onAddNew();
    } else {
      onPick(items[idx]);
    }
    setOpen(false);
  }

  function onKeyDown(event) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setOpen(true);
      setActiveIndex((i) => Math.min(i + 1, totalRows - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (open) pickItem(activeIndex);
      else setOpen(true);
    } else if (event.key === "Escape") {
      setOpen(false);
    }
  }

  const selectedNode = items.find((p) => p.id === value);
  const inputValue = selectedNode && !open ? selectedNode.display_name : query;

  return (
    <div className="productor-selector__combobox" ref={containerRef}>
      <div className="productor-selector__combobox-input">
        <Search
          size={14}
          aria-hidden="true"
          className="productor-selector__combobox-icon"
        />
        <input
          type="text"
          aria-label="Buscar productorx"
          placeholder="Buscar productor o agregar uno nuevo"
          value={inputValue}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
            setActiveIndex(0);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
        />
      </div>
      {open && (
        <ul className="productor-selector__combobox-list" role="listbox">
          {items.map((p, idx) => (
            <li
              key={p.id}
              role="option"
              aria-selected={idx === activeIndex}
              className={
                idx === activeIndex
                  ? "productor-selector__combobox-option productor-selector__combobox-option--active"
                  : "productor-selector__combobox-option"
              }
              onMouseEnter={() => setActiveIndex(idx)}
              onClick={() => pickItem(idx)}
            >
              {p.display_name}
            </li>
          ))}
          <li
            role="option"
            aria-selected={items.length === activeIndex}
            className={
              items.length === activeIndex
                ? "productor-selector__combobox-add productor-selector__combobox-add--active"
                : "productor-selector__combobox-add"
            }
            onMouseEnter={() => setActiveIndex(items.length)}
            onClick={() => pickItem(items.length)}
          >
            <Plus size={14} aria-hidden="true" />
            <span>Agregar nuevo productor</span>
          </li>
        </ul>
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
        cuit: cuit.trim() || null,
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
        <div className="productor-modal__top-row">
          <h2 id="productor-modal-title" className="productor-modal__title">
            Agregar productorx
          </h2>
          <button
            type="button"
            className="productor-modal__close"
            onClick={onCancel}
            aria-label="Cerrar"
          >
            <X size={20} aria-hidden="true" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="productor-modal__form">
          <Input
            id="productor-cuit"
            label="CUIT (opcional)"
            value={cuit}
            onChange={(e) => setCuit(e.target.value)}
            placeholder="20-12345678-9"
          />
          <Input
            id="productor-name"
            label="Nombre o razón social"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="Ej. Finca El Nogal"
            required
          />
          <div className="productor-modal__address-group">
            <Input
              id="productor-address"
              label="Dirección"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="Calle, localidad, provincia"
              required
            />
            <p className="productor-modal__helper">
              Trama va a geocodificar esta dirección para ubicar al productorx
              en el mapa.
            </p>
          </div>
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
