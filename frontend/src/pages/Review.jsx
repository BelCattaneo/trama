import { useEffect, useMemo, useState } from "react";
import { useBlocker, useNavigate, useParams } from "react-router-dom";
import { CircleAlert, Loader, Trash2, TriangleAlert } from "lucide-react";
import NavBarAuth from "../components/NavBarAuth";
import ProductorSelector from "../components/ProductorSelector";
import { apiDelete, apiGet, apiPost } from "../lib/api";
import { useReviewState } from "../lib/useReviewState";
import ReviewPreview from "./ReviewPreview";
import ReviewLines from "./ReviewLines";
import "./Review.css";

const ALL_PAGES = "all";
const NAV_GUARD_MESSAGE = "¿salir sin confirmar? los cambios se perderán";

export default function Review() {
  const { document_id } = useParams();
  const [state, setState] = useState({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      try {
        const response = await apiGet(`/api/documents/${document_id}/review`, {
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        if (!response.ok) {
          setState({ status: "error" });
          return;
        }
        const body = await response.json();
        setState({ status: "ready", body });
      } catch (err) {
        if (err.name === "AbortError") return;
        setState({ status: "error" });
      }
    })();
    return () => controller.abort();
  }, [document_id]);

  if (state.status === "loading") {
    return (
      <div className="page-shell review-page">
        <NavBarAuth />
        <main className="review-page__content">
          <div className="review-page__status" role="status">
            <Loader size={24} aria-hidden="true" />
            <span>Cargando…</span>
          </div>
        </main>
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div className="page-shell review-page">
        <NavBarAuth />
        <main className="review-page__content">
          <div
            className="review-page__status review-page__status--error"
            role="alert"
          >
            No pudimos cargar el documento.
          </div>
        </main>
      </div>
    );
  }

  return <ReviewLoaded documentId={document_id} body={state.body} />;
}

function ReviewLoaded({ documentId, body }) {
  const navigate = useNavigate();
  const { document, parse_attempt, supplier_detection } = body;
  const payload = useMemo(
    () => parse_attempt?.payload ?? { lines: [], warnings: [] },
    [parse_attempt],
  );
  const confidence = parse_attempt?.confidence ?? 0;
  const errorMessage = parse_attempt?.error_message ?? null;
  const isWinner = parse_attempt?.is_winner ?? false;
  const isPdf = document.mime_type === "application/pdf";

  const initialSupplierNodeId = supplier_detection?.matched_node?.id ?? null;
  const [supplierNodeId, setSupplierNodeId] = useState(initialSupplierNodeId);

  const {
    lines,
    addLine,
    removeLine,
    updateField,
    getCorrections,
    getFinalPayload,
  } = useReviewState(payload);

  const totalPages = useMemo(() => {
    if (!isPdf) return 1;
    const pageNumbers = payload.lines
      .map((line) => line.page)
      .filter((page) => typeof page === "number" && page > 0);
    return pageNumbers.length === 0 ? 1 : Math.max(...pageNumbers);
  }, [isPdf, payload.lines]);

  const [activePage, setActivePage] = useState(
    isPdf && totalPages > 1 ? 1 : ALL_PAGES,
  );
  const [warningsOpen, setWarningsOpen] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [toast, setToast] = useState("");

  const hasUnsavedChanges = useMemo(
    () =>
      getCorrections().length > 0 || supplierNodeId !== initialSupplierNodeId,
    [getCorrections, supplierNodeId, initialSupplierNodeId],
  );

  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      hasUnsavedChanges &&
      !submitting &&
      currentLocation.pathname !== nextLocation.pathname,
  );

  useEffect(() => {
    if (blocker.state === "blocked") {
      const confirmed = window.confirm(NAV_GUARD_MESSAGE);
      if (confirmed) blocker.proceed();
      else blocker.reset();
    }
  }, [blocker]);

  useEffect(() => {
    if (!hasUnsavedChanges) return undefined;
    const onBeforeUnload = (event) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [hasUnsavedChanges]);

  const visibleLines = useMemo(() => {
    if (!isPdf || activePage === ALL_PAGES) return lines;
    return lines.filter((line) => line.page === activePage);
  }, [lines, isPdf, activePage]);

  const visibleWarnings = useMemo(() => {
    const warnings = payload.warnings ?? [];
    if (!isPdf || activePage === ALL_PAGES) return warnings;
    const prefix = `[p${activePage}]`;
    return warnings.filter((w) => w.startsWith(prefix));
  }, [payload.warnings, isPdf, activePage]);

  const hasInvalid =
    lines.length === 0 ||
    lines.some(
      (line) =>
        line.product === "" ||
        line.product === "unreadable" ||
        line.quantity === 0,
    );
  const confirmDisabled = isWinner || submitting || hasInvalid;

  async function onConfirm() {
    setSubmitting(true);
    setToast("");
    try {
      const response = await apiPost(`/api/documents/${documentId}/confirm`, {
        lines: getFinalPayload().lines,
        corrections: getCorrections(),
        supplier_node_id: supplierNodeId,
      });
      if (response.status === 200 || response.status === 201) {
        const result = await response.json();
        navigate(`/my-orders?highlight=${result.operation_id}`);
        return;
      }
      const errorBody = await response.json().catch(() => ({}));
      setToast(errorBody.error || "No pudimos confirmar el documento.");
    } catch {
      setToast("No pudimos confirmar el documento.");
    } finally {
      setSubmitting(false);
    }
  }

  async function onDelete() {
    if (
      !window.confirm(
        "¿Eliminar este documento? Esta acción no se puede deshacer.",
      )
    ) {
      return;
    }
    setSubmitting(true);
    setToast("");
    try {
      const response = await apiDelete(`/api/documents/${documentId}`);
      if (response.status === 204) {
        navigate("/documents", { replace: true });
        return;
      }
      const errorBody = await response.json().catch(() => ({}));
      setToast(errorBody.error || "No pudimos eliminar el documento.");
    } catch {
      setToast("No pudimos eliminar el documento.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page-shell review-page">
      <NavBarAuth />
      <main className="review-page__content">
        <Banners confidence={confidence} isWinner={isWinner} />

        {errorMessage && (
          <div className="review-page__error" role="alert">
            <CircleAlert size={18} aria-hidden="true" />
            <span>{errorMessage}</span>
          </div>
        )}

        <div className="review-page__split">
          <section className="review-page__preview">
            {isPdf && totalPages > 1 && (
              <PageTabs
                totalPages={totalPages}
                activePage={activePage}
                onChange={setActivePage}
              />
            )}
            <ReviewPreview
              document={document}
              activePage={activePage === ALL_PAGES ? 1 : activePage}
            />
          </section>

          <section className="review-page__right">
            <WarningsPanel
              warnings={visibleWarnings}
              open={warningsOpen}
              onToggle={() => setWarningsOpen((current) => !current)}
              hasError={!!errorMessage || confidence === 0}
            />
            <ProductorSelector
              detection={supplier_detection}
              value={supplierNodeId}
              onChange={setSupplierNodeId}
            />
            {supplierNodeId === null && (
              <p className="review-page__supplier-warning" role="status">
                Este pedido va a quedar sin productorx asignadx. Podés seguir o
                seleccionar unx arriba.
              </p>
            )}
            <ReviewLines
              lines={visibleLines}
              readOnly={isWinner}
              onUpdate={updateField}
              onRemove={removeLine}
              onAdd={addLine}
              groupByPage={isPdf && activePage === ALL_PAGES && totalPages > 1}
            />
          </section>
        </div>

        {toast && (
          <div className="review-page__toast" role="alert">
            {toast}
          </div>
        )}
      </main>

      {!isWinner && (
        <footer className="review-page__footer">
          <button
            type="button"
            className="review-page__delete"
            disabled={submitting}
            onClick={onDelete}
          >
            <Trash2 size={16} aria-hidden="true" />
            <span>Eliminar</span>
          </button>
          <button
            type="button"
            className="review-page__confirm"
            disabled={confirmDisabled}
            onClick={onConfirm}
          >
            {submitting ? "Confirmando…" : "Confirmar"}
          </button>
        </footer>
      )}
    </div>
  );
}

function Banners({ confidence, isWinner }) {
  if (isWinner) {
    return (
      <div
        className="review-page__banner review-page__banner--info"
        role="status"
      >
        Este documento ya fue confirmado.
      </div>
    );
  }
  if (confidence === 0) {
    return (
      <div
        className="review-page__banner review-page__banner--error"
        role="alert"
      >
        No se pudo parsear automáticamente, ingresá las líneas a mano.
      </div>
    );
  }
  if (confidence < 0.5) {
    return (
      <div
        className="review-page__banner review-page__banner--warning"
        role="status"
      >
        El sistema no estaba seguro, revisá con cuidado.
      </div>
    );
  }
  return null;
}

function WarningsPanel({ warnings, open, onToggle, hasError }) {
  if (warnings.length === 0) return null;
  // Errors render red; everything else is yellow per ticket scheme.
  const severity = hasError ? "error" : "warning";
  const count = warnings.length;
  const label = count === 1 ? "1 advertencia" : `${count} advertencias`;
  return (
    <section className="review-page__warnings">
      <button
        type="button"
        className="review-page__warnings-header"
        onClick={onToggle}
        aria-expanded={open}
      >
        <TriangleAlert size={16} aria-hidden="true" />
        <span>{label}</span>
        <span aria-hidden="true">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <ul className="review-page__warnings-list">
          {warnings.map((warning, idx) => (
            <li
              key={`${idx}-${warning}`}
              className={`review-page__warnings-item review-page__warnings-item--${severity}`}
              data-severity={severity}
            >
              {warning}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function PageTabs({ totalPages, activePage, onChange }) {
  const pages = Array.from({ length: totalPages }, (_, i) => i + 1);
  if (totalPages > 5) {
    return (
      <div className="review-page__tabs">
        <label className="review-page__tabs-label" htmlFor="review-page-select">
          Página
        </label>
        <select
          id="review-page-select"
          className="review-page__tabs-select"
          value={activePage}
          onChange={(event) => {
            const value = event.target.value;
            onChange(value === ALL_PAGES ? ALL_PAGES : Number(value));
          }}
        >
          <option value={ALL_PAGES}>Todas las páginas</option>
          {pages.map((page) => (
            <option key={page} value={page}>
              Página {page}
            </option>
          ))}
        </select>
      </div>
    );
  }
  return (
    <div className="review-page__tabs" role="tablist">
      <button
        type="button"
        role="tab"
        aria-selected={activePage === ALL_PAGES}
        className={
          activePage === ALL_PAGES
            ? "review-page__tab review-page__tab--active"
            : "review-page__tab"
        }
        onClick={() => onChange(ALL_PAGES)}
      >
        Todas las páginas
      </button>
      {pages.map((page) => (
        <button
          key={page}
          type="button"
          role="tab"
          aria-selected={activePage === page}
          className={
            activePage === page
              ? "review-page__tab review-page__tab--active"
              : "review-page__tab"
          }
          onClick={() => onChange(page)}
        >
          Página {page}
        </button>
      ))}
    </div>
  );
}
