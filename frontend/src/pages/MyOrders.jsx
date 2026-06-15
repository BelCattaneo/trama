import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Loader, PackageOpen } from "lucide-react";
import NavBarAuth from "../components/NavBarAuth";
import { apiGet } from "../lib/api";
import "./MyOrders.css";

const dateFormatter = new Intl.DateTimeFormat("es-AR", {
  day: "2-digit",
  month: "short",
  year: "numeric",
});

function formatDate(value) {
  if (!value) return "";
  // operation_date is a DATE (YYYY-MM-DD). Parse as local to avoid timezone shifts.
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) return "";
  const date = new Date(year, month - 1, day);
  if (Number.isNaN(date.getTime())) return "";
  return dateFormatter.format(date);
}

function kindLabel(kind) {
  if (kind === "order") return "pedido";
  if (kind === "offer") return "oferta";
  return kind ?? "";
}

const HIGHLIGHT_MS = 3000;

export default function MyOrders() {
  const navigate = useNavigate();
  const [state, setState] = useState({ status: "loading", operations: [] });
  const [searchParams] = useSearchParams();
  const highlightId = searchParams.get("highlight");
  const [activeHighlight, setActiveHighlight] = useState(highlightId);

  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      try {
        const response = await apiGet("/api/operations?limit=200", {
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        if (response.status === 401) {
          navigate("/login", { replace: true });
          return;
        }
        if (!response.ok) {
          const body = await response.json().catch(() => ({}));
          setState({
            status: "error",
            operations: [],
            error: body.error || "No pudimos cargar tus pedidos.",
          });
          return;
        }
        const body = await response.json();
        const operations = body.items ?? [];
        setState({
          status: operations.length === 0 ? "empty" : "list",
          operations,
        });
      } catch (err) {
        if (err.name === "AbortError") return;
        setState({
          status: "error",
          operations: [],
          error: "No pudimos cargar tus pedidos.",
        });
      }
    })();
    return () => controller.abort();
  }, [navigate]);

  useEffect(() => {
    if (!activeHighlight) return undefined;
    const matches = state.operations.some((op) => op.id === activeHighlight);
    if (!matches) return undefined;
    const timer = setTimeout(() => setActiveHighlight(null), HIGHLIGHT_MS);
    return () => clearTimeout(timer);
  }, [activeHighlight, state.operations]);

  return (
    <div className="page-shell my-orders-page">
      <NavBarAuth />
      <main className="my-orders-page__content">
        <header className="my-orders-page__header">
          <h1 className="my-orders-page__title">Mis pedidos</h1>
        </header>

        {state.status === "loading" && (
          <div
            className="my-orders-page__status my-orders-page__status--loading"
            role="status"
          >
            <Loader
              size={24}
              aria-hidden="true"
              className="my-orders-page__spinner"
            />
            <span>cargando…</span>
          </div>
        )}

        {state.status === "error" && (
          <div className="my-orders-page__toast" role="alert">
            {state.error}
          </div>
        )}

        {state.status === "empty" && (
          <div className="my-orders-page__empty">
            <PackageOpen size={40} aria-hidden="true" />
            <p>todavía no confirmaste ningún pedido</p>
            <Link to="/upload" className="my-orders-page__empty-cta">
              subir documento
            </Link>
          </div>
        )}

        {state.status === "list" && (
          <OperationsTable
            operations={state.operations}
            highlightId={activeHighlight}
          />
        )}
      </main>
    </div>
  );
}

function OperationsTable({ operations, highlightId }) {
  return (
    <>
      <table className="my-orders-page__table">
        <thead>
          <tr>
            <th>Fecha</th>
            <th>Cantidad de líneas</th>
            <th>Tipo</th>
            <th>Acción</th>
          </tr>
        </thead>
        <tbody>
          {operations.map((op) => {
            const isHighlighted = op.id === highlightId;
            const rowClass = isHighlighted
              ? "my-orders-page__row highlighted-row"
              : "my-orders-page__row";
            return (
              <tr key={op.id} className={rowClass} data-testid={`row-${op.id}`}>
                <td>{formatDate(op.operation_date)}</td>
                <td>{op.line_count}</td>
                <td>{kindLabel(op.kind)}</td>
                <td>
                  <Link
                    to={`/my-orders/${op.id}`}
                    className="my-orders-page__detail-link"
                  >
                    ver detalle
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <ul className="my-orders-page__cards">
        {operations.map((op) => {
          const isHighlighted = op.id === highlightId;
          const cardClass = isHighlighted
            ? "my-orders-page__card highlighted-row"
            : "my-orders-page__card";
          return (
            <li key={op.id} className={cardClass} data-testid={`card-${op.id}`}>
              <div className="my-orders-page__card-row">
                <span className="my-orders-page__card-label">Fecha</span>
                <span>{formatDate(op.operation_date)}</span>
              </div>
              <div className="my-orders-page__card-row">
                <span className="my-orders-page__card-label">
                  Cantidad de líneas
                </span>
                <span>{op.line_count}</span>
              </div>
              <div className="my-orders-page__card-row">
                <span className="my-orders-page__card-label">Tipo</span>
                <span>{kindLabel(op.kind)}</span>
              </div>
              <Link
                to={`/my-orders/${op.id}`}
                className="my-orders-page__detail-link"
              >
                ver detalle
              </Link>
            </li>
          );
        })}
      </ul>
    </>
  );
}
