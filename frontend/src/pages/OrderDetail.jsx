import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Download, ExternalLink, Loader } from "lucide-react";
import NavBarAuth from "../components/NavBarAuth";
import { apiGet } from "../lib/api";
import { buildOperationCsv, buildOperationFilename } from "../lib/csv";
import "./OrderDetail.css";

const dateFormatter = new Intl.DateTimeFormat("es-AR", {
  day: "2-digit",
  month: "short",
  year: "numeric",
});

function formatOperationDate(value) {
  if (!value) return "";
  // operation_date is a DATE (YYYY-MM-DD). Parse as local to avoid timezone shifts.
  const [year, month, day] = value.split("-").map(Number);
  const date = new Date(year, month - 1, day);
  return dateFormatter.format(date);
}

export default function OrderDetail() {
  const { operation_id } = useParams();
  const navigate = useNavigate();
  const [state, setState] = useState({ status: "loading" });
  const [toast, setToast] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      try {
        const response = await apiGet(`/api/operations/${operation_id}`, {
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        if (response.status === 401) {
          navigate("/login", { replace: true });
          return;
        }
        if (response.status === 404) {
          navigate("/my-orders", {
            replace: true,
            state: { toast: "pedido no encontrado" },
          });
          return;
        }
        if (!response.ok) {
          const errorBody = await response.json().catch(() => ({}));
          setToast(errorBody.error || "no pudimos cargar el pedido");
          setState({ status: "error" });
          return;
        }
        const body = await response.json();
        setState({ status: "ready", body });
      } catch (err) {
        if (err.name === "AbortError") return;
        setToast("no pudimos cargar el pedido");
        setState({ status: "error" });
      }
    })();
    return () => controller.abort();
  }, [operation_id, navigate]);

  if (state.status === "loading") {
    return (
      <div className="page-shell order-detail">
        <NavBarAuth />
        <main className="order-detail__content">
          <div className="order-detail__status" role="status">
            <Loader
              size={24}
              aria-hidden="true"
              className="order-detail__spinner"
            />
            <span>cargando…</span>
          </div>
        </main>
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div className="page-shell order-detail">
        <NavBarAuth />
        <main className="order-detail__content">
          {toast && (
            <div className="order-detail__toast" role="alert">
              {toast}
            </div>
          )}
        </main>
      </div>
    );
  }

  const { body } = state;
  const lines = body.lines ?? [];
  const showPageColumn = lines.some((line) => line.page !== null);

  function onDownloadCsv() {
    const content = buildOperationCsv(lines);
    const filename = buildOperationFilename({
      kind: body.kind,
      operationDate: body.operation_date,
      id: body.id,
    });
    const blob = new Blob([content], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  return (
    <div className="page-shell order-detail">
      <NavBarAuth />
      <main className="order-detail__content">
        <header className="order-detail__header">
          <div className="order-detail__header-top">
            <Link to="/my-orders" className="order-detail__back">
              <ArrowLeft size={16} aria-hidden="true" />
              <span>volver</span>
            </Link>
            <div className="order-detail__header-actions">
              <button
                type="button"
                className="order-detail__csv-link"
                onClick={onDownloadCsv}
                disabled={lines.length === 0}
              >
                <Download size={16} aria-hidden="true" />
                <span>descargar CSV</span>
              </button>
              {body.document_id && (
                <a
                  className="order-detail__file-link"
                  href={`/api/documents/${body.document_id}/file`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <ExternalLink size={16} aria-hidden="true" />
                  <span>ver archivo original</span>
                </a>
              )}
            </div>
          </div>
          <dl className="order-detail__meta">
            <div className="order-detail__meta-item">
              <dt>Fecha</dt>
              <dd>{formatOperationDate(body.operation_date)}</dd>
            </div>
            <div className="order-detail__meta-item">
              <dt>Cantidad de líneas</dt>
              <dd>{lines.length}</dd>
            </div>
          </dl>
        </header>

        <table className="order-detail__table">
          <thead>
            <tr>
              <th>Producto</th>
              <th>Cantidad</th>
              <th>Unidad</th>
              {showPageColumn && <th>Página</th>}
            </tr>
          </thead>
          <tbody>
            {lines.map((line, idx) => (
              <tr key={line.line_no ?? idx}>
                <td data-label="Producto">{line.product}</td>
                <td data-label="Cantidad">{line.quantity}</td>
                <td data-label="Unidad">{line.unit}</td>
                {showPageColumn && (
                  <td data-label="Página">{line.page ?? ""}</td>
                )}
              </tr>
            ))}
          </tbody>
        </table>

        {toast && (
          <div className="order-detail__toast" role="alert">
            {toast}
          </div>
        )}
      </main>
    </div>
  );
}
