import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ChevronRight, FileText, Loader } from "lucide-react";
import ConfidenceBadge, { documentStatus } from "../components/ConfidenceBadge";
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
  const navigate = useNavigate();
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
        setState({
          status: body.documents.length === 0 ? "empty" : "list",
          documents: body.documents,
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
          <div className="docs-page__table-card">
            <table className="docs-page__table">
              <thead>
                <tr>
                  <th>Nombre</th>
                  <th>Fecha</th>
                  <th>Tipo</th>
                  <th>Estado</th>
                  <th aria-hidden="true" />
                </tr>
              </thead>
              <tbody>
                {state.documents.map((doc) => {
                  const status = documentStatus({
                    hasParseAttempt: doc.has_parse_attempt,
                    hasWinner: doc.has_winner,
                    latestConfidence: doc.latest_confidence,
                    latestErrorMessage: doc.latest_error_message,
                  });
                  return (
                    <tr
                      key={doc.id}
                      className="docs-page__row"
                      tabIndex={0}
                      role="link"
                      onClick={() => navigate(`/review/${doc.id}`)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          navigate(`/review/${doc.id}`);
                        }
                      }}
                    >
                      <td>{doc.original_filename}</td>
                      <td>{dateFormatter.format(new Date(doc.uploaded_at))}</td>
                      <td>{MIME_LABELS[doc.mime_type] ?? "Archivo"}</td>
                      <td>
                        <ConfidenceBadge status={status} />
                      </td>
                      <td className="docs-page__row-chevron" aria-hidden="true">
                        <ChevronRight size={16} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}
