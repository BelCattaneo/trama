import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { FileText, Loader } from "lucide-react";
import NavBarAuth from "../components/NavBarAuth";
import { useAuth } from "../contexts/AuthContext";
import { apiGet } from "../lib/api";
import { operationLabels } from "../lib/roleLabels";
import "./DocumentsList.css";

const MIME_LABELS = {
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
    "Planilla Excel",
  "text/csv": "CSV",
  "image/jpeg": "Imagen",
  "image/png": "Imagen",
  "application/pdf": "PDF",
};

const dateFormatter = new Intl.DateTimeFormat("es-AR", {
  day: "numeric",
  month: "short",
  year: "numeric",
});

export default function DocumentsList() {
  const { user } = useAuth();
  const labels = operationLabels(user?.node?.role);
  const [state, setState] = useState({ status: "loading", documents: [] });

  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      try {
        const response = await apiGet("/api/documents", {
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        if (!response.ok) {
          setState({ status: "error", documents: [] });
          return;
        }
        const body = await response.json();
        const docs = body.documents || [];
        setState({
          status: docs.length === 0 ? "empty" : "list",
          documents: docs,
        });
      } catch (err) {
        if (err.name === "AbortError") return;
        setState({ status: "error", documents: [] });
      }
    })();
    return () => controller.abort();
  }, []);

  return (
    <div className="page-shell docs-page">
      <NavBarAuth />
      <main className="docs-page__content">
        <header className="docs-page__header">
          <h1 className="docs-page__title">Mis documentos</h1>
          <Link to="/upload" className="docs-page__cta">
            {labels.action}
          </Link>
        </header>

        {state.status === "loading" && (
          <div
            className="docs-page__status docs-page__status--loading"
            role="status"
          >
            <Loader
              size={24}
              aria-hidden="true"
              className="docs-page__spinner"
            />
            <span>Cargando…</span>
          </div>
        )}

        {state.status === "error" && (
          <div
            className="docs-page__status docs-page__status--error"
            role="alert"
          >
            No pudimos cargar tus documentos. Intentá de nuevo.
          </div>
        )}

        {state.status === "empty" && (
          <div className="docs-page__empty">
            <FileText size={40} aria-hidden="true" />
            <p>Todavía no subiste documentos.</p>
            <Link to="/upload" className="docs-page__empty-cta">
              {labels.firstAction}
            </Link>
          </div>
        )}

        {state.status === "list" && (
          <table className="docs-page__table">
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Fecha</th>
                <th>Tipo</th>
              </tr>
            </thead>
            <tbody>
              {state.documents.map((doc) => (
                <tr key={doc.id}>
                  <td>{doc.original_filename}</td>
                  <td>{dateFormatter.format(new Date(doc.uploaded_at))}</td>
                  <td>{MIME_LABELS[doc.mime_type] || doc.mime_type}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </main>
    </div>
  );
}
