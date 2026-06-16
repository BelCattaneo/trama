import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  CheckCircle2,
  Download,
  ExternalLink,
  ListChecks,
  Loader,
  Trash2,
} from "lucide-react";
import NavBarAuth from "../components/NavBarAuth";
import ProductorSelector from "../components/ProductorSelector";
import { apiDelete, apiGet, apiPatch } from "../lib/api";
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
  const [deleting, setDeleting] = useState(false);
  const [editingSupplier, setEditingSupplier] = useState(false);
  const [pendingSupplierId, setPendingSupplierId] = useState(null);
  const [savingSupplier, setSavingSupplier] = useState(false);

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

  async function onSaveSupplier() {
    setSavingSupplier(true);
    setToast("");
    try {
      const response = await apiPatch(`/api/operations/${body.id}`, {
        supplier_node_id: pendingSupplierId,
      });
      if (response.status === 204) {
        setState({
          ...state,
          body: { ...body, supplier_display_name: null, supplier_cuit: null },
        });
        const refreshed = await apiGet(`/api/operations/${body.id}`);
        if (refreshed.ok) {
          const fresh = await refreshed.json();
          setState({ status: "ready", body: fresh });
        }
        setEditingSupplier(false);
        return;
      }
      const errorBody = await response.json().catch(() => ({}));
      setToast(errorBody.error || "No pudimos guardar el productor.");
    } catch {
      setToast("No pudimos guardar el productor.");
    } finally {
      setSavingSupplier(false);
    }
  }

  async function onDelete() {
    if (
      !window.confirm(
        "¿Eliminar este pedido? Esta acción no se puede deshacer.",
      )
    ) {
      return;
    }
    setDeleting(true);
    setToast("");
    try {
      const response = await apiDelete(`/api/operations/${body.id}`);
      if (response.status === 204) {
        navigate("/my-orders", {
          replace: true,
          state: { toast: "pedido eliminado" },
        });
        return;
      }
      const errorBody = await response.json().catch(() => ({}));
      setToast(errorBody.error || "No pudimos eliminar el pedido.");
    } catch {
      setToast("No pudimos eliminar el pedido.");
    } finally {
      setDeleting(false);
    }
  }

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
              <button
                type="button"
                className="order-detail__delete"
                onClick={onDelete}
                disabled={deleting}
              >
                <Trash2 size={16} aria-hidden="true" />
                <span>eliminar pedido</span>
              </button>
            </div>
          </div>
          {toast && (
            <div className="order-detail__toast" role="alert">
              {toast}
            </div>
          )}
          <h1 className="order-detail__title">
            Pedido del {formatOperationDate(body.operation_date)}
          </h1>
        </header>

        <div className="order-detail__stats">
          <div className="order-detail__stat">
            <div className="order-detail__stat-icon" aria-hidden="true">
              <ListChecks size={20} />
            </div>
            <div className="order-detail__stat-text">
              <span className="order-detail__stat-value">{lines.length}</span>
              <span className="order-detail__stat-label">Líneas totales</span>
            </div>
          </div>
          <div className="order-detail__stat">
            <div className="order-detail__stat-icon" aria-hidden="true">
              <CheckCircle2 size={20} />
            </div>
            <div className="order-detail__stat-text">
              <span className="order-detail__stat-value">
                {formatOperationDate(body.operation_date)}
              </span>
              <span className="order-detail__stat-label">Confirmado</span>
            </div>
          </div>
        </div>

        <div className="order-detail__supplier">
          {!editingSupplier ? (
            <>
              <div className="order-detail__supplier-header">
                <p className="order-detail__supplier-label">
                  PRODUCTOR DEL PEDIDO
                </p>
                <button
                  type="button"
                  className="order-detail__supplier-edit"
                  onClick={() => {
                    setPendingSupplierId(null);
                    setEditingSupplier(true);
                  }}
                >
                  {body.supplier_display_name ? "Cambiar" : "Asignar"}
                </button>
              </div>
              {body.supplier_display_name ? (
                <div className="order-detail__supplier-info">
                  <p className="order-detail__supplier-name">
                    {body.supplier_display_name}
                  </p>
                  {body.supplier_cuit && (
                    <p className="order-detail__supplier-cuit">
                      CUIT {body.supplier_cuit}
                    </p>
                  )}
                </div>
              ) : (
                <p className="order-detail__supplier-empty">
                  Este pedido no tiene productor asignado
                </p>
              )}
            </>
          ) : (
            <>
              <ProductorSelector
                detection={null}
                value={pendingSupplierId}
                onChange={setPendingSupplierId}
              />
              <div className="order-detail__supplier-actions">
                <button
                  type="button"
                  className="order-detail__supplier-cancel"
                  onClick={() => setEditingSupplier(false)}
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  className="order-detail__supplier-save"
                  onClick={onSaveSupplier}
                  disabled={savingSupplier || !pendingSupplierId}
                >
                  Guardar
                </button>
              </div>
            </>
          )}
        </div>

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
            {lines.map((line) => (
              <tr key={line.line_no}>
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
      </main>
    </div>
  );
}
