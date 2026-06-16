import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  CalendarClock,
  ChevronRight,
  ListChecks,
  Loader,
  PackageCheck,
  PackageOpen,
} from "lucide-react";
import ConfidenceBadge from "../components/ConfidenceBadge";
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

function operationsCountLabel(count) {
  if (count === 1) return "1 pedido confirmado";
  return `${count} pedidos confirmados`;
}

export function computeStats(operations) {
  const totalLines = operations.reduce(
    (sum, op) => sum + (op.line_count ?? 0),
    0,
  );
  const latest = operations.reduce((acc, op) => {
    if (!op.operation_date) return acc;
    if (!acc) return op.operation_date;
    return op.operation_date > acc ? op.operation_date : acc;
  }, null);
  return {
    confirmed: operations.length,
    totalLines,
    latestDate: latest,
  };
}

function StatCard({ icon: Icon, value, label }) {
  return (
    <div className="my-orders-page__stat">
      <div className="my-orders-page__stat-icon" aria-hidden="true">
        <Icon size={20} />
      </div>
      <div className="my-orders-page__stat-text">
        <span className="my-orders-page__stat-value">{value}</span>
        <span className="my-orders-page__stat-label">{label}</span>
      </div>
    </div>
  );
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
        {state.status !== "empty" && (
          <header className="my-orders-page__header">
            <h1 className="my-orders-page__title">Mis pedidos</h1>
            <div className="my-orders-page__header-right">
              {state.status === "list" && (
                <p className="my-orders-page__subtitle">
                  {operationsCountLabel(state.operations.length)}
                </p>
              )}
              <Link to="/upload" className="my-orders-page__upload-cta">
                Subir pedido
              </Link>
            </div>
          </header>
        )}

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
            <div className="my-orders-page__empty-icon-circle" aria-hidden="true">
              <PackageOpen size={28} />
            </div>
            <h2 className="my-orders-page__empty-title">
              Todavía no tenés pedidos
            </h2>
            <p className="my-orders-page__empty-desc">
              Cuando subas una planilla y confirmes las líneas,
              <br />
              tus pedidos van a aparecer acá.
            </p>
            <Link to="/upload" className="my-orders-page__empty-cta">
              Subir mi primer pedido
            </Link>
          </div>
        )}

        {state.status === "list" && (
          <>
            <StatsBar operations={state.operations} />
            <OperationsTable
              operations={state.operations}
              highlightId={activeHighlight}
              navigate={navigate}
            />
          </>
        )}
      </main>
    </div>
  );
}

function StatsBar({ operations }) {
  const stats = computeStats(operations);
  return (
    <div className="my-orders-page__stats">
      <StatCard
        icon={PackageCheck}
        value={stats.confirmed}
        label="Pedidos confirmados"
      />
      <StatCard
        icon={ListChecks}
        value={stats.totalLines}
        label="Líneas totales"
      />
      <StatCard
        icon={CalendarClock}
        value={stats.latestDate ? formatDate(stats.latestDate) : "—"}
        label="Último pedido"
      />
    </div>
  );
}

function OperationsTable({ operations, highlightId, navigate }) {
  return (
    <>
      <div className="my-orders-page__table-card">
        <table className="my-orders-page__table">
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Origen</th>
              <th>Productor</th>
              <th>Líneas</th>
              <th>Estado</th>
              <th aria-hidden="true" />
            </tr>
          </thead>
          <tbody>
            {operations.map((op) => {
              const isHighlighted = op.id === highlightId;
              const rowClass = isHighlighted
                ? "my-orders-page__row highlighted-row"
                : "my-orders-page__row";
              return (
                <tr
                  key={op.id}
                  className={rowClass}
                  data-testid={`row-${op.id}`}
                  tabIndex={0}
                  role="link"
                  onClick={() => navigate(`/my-orders/${op.id}`)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      navigate(`/my-orders/${op.id}`);
                    }
                  }}
                >
                  <td>{formatDate(op.operation_date)}</td>
                  <td className="my-orders-page__origen">
                    {op.source_filename || "—"}
                  </td>
                  <td>{op.supplier_display_name || "—"}</td>
                  <td>{op.line_count}</td>
                  <td>
                    <ConfidenceBadge status="confirmed" />
                  </td>
                  <td
                    className="my-orders-page__row-chevron"
                    aria-hidden="true"
                  >
                    <ChevronRight size={16} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
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
              {op.source_filename && (
                <div className="my-orders-page__card-row">
                  <span className="my-orders-page__card-label">Origen</span>
                  <span>{op.source_filename}</span>
                </div>
              )}
              {op.supplier_display_name && (
                <div className="my-orders-page__card-row">
                  <span className="my-orders-page__card-label">Productor</span>
                  <span>{op.supplier_display_name}</span>
                </div>
              )}
              <div className="my-orders-page__card-row">
                <span className="my-orders-page__card-label">Líneas</span>
                <span>{op.line_count}</span>
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
