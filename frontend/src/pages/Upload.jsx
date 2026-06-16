import { useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { CircleAlert, Loader, Upload as UploadIcon } from "lucide-react";
import NavBarAuth from "../components/NavBarAuth";
import { useAuth } from "../contexts/AuthContext";
import { apiPostForm } from "../lib/api";
import { operationLabels } from "../lib/roleLabels";
import {
  ACCEPTED_EXTENSIONS,
  validateClientFile,
} from "../lib/uploadValidation";
import "./Upload.css";

export default function Upload() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [filename, setFilename] = useState("");
  const [error, setError] = useState("");
  const labels = operationLabels(user?.node?.role);

  async function handleFile(file) {
    const validation = validateClientFile(file);
    if (!validation.ok) {
      setError(validation.error);
      return;
    }
    setError("");
    setFilename(file.name);
    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const response = await apiPostForm("/api/documents", formData);
      if (response.status === 201) {
        const body = await response.json().catch(() => null);
        const documentId = body?.document?.id;
        if (!documentId) {
          setError("No pudimos subir el archivo, intentá de nuevo.");
          return;
        }
        navigate(`/review/${documentId}`);
        return;
      }
      if (response.status === 401) {
        navigate("/login", {
          state: {
            message: "Tu sesión expiró. Iniciá sesión de nuevo.",
          },
          replace: true,
        });
        return;
      }
      const body = await response.json().catch(() => ({}));
      setError(body.error || "No pudimos subir el archivo, intentá de nuevo.");
    } catch {
      setError("Error de conexión, intentá de nuevo.");
    } finally {
      setUploading(false);
    }
  }

  function onPick(event) {
    const file = event.target.files?.[0];
    if (file) handleFile(file);
    event.target.value = "";
  }

  function onDrop(event) {
    event.preventDefault();
    setDragging(false);
    const file = event.dataTransfer.files?.[0];
    if (file) handleFile(file);
  }

  function onDragOver(event) {
    event.preventDefault();
    setDragging(true);
  }

  function onDragLeave() {
    setDragging(false);
  }

  return (
    <div className="page-shell upload-page">
      <NavBarAuth />
      <main className="upload-page__content">
        <header className="upload-page__header">
          <h1 className="upload-page__title">{labels.action}</h1>
          <p className="upload-page__lead">
            Subí tu planilla, foto o PDF con el pedido. Trama se encarga de
            interpretarlo.
          </p>
        </header>

        {!uploading && (
          <div
            className={
              dragging
                ? "upload-page__drop upload-page__drop--active"
                : "upload-page__drop"
            }
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            onDrop={onDrop}
          >
            <UploadIcon
              size={48}
              aria-hidden="true"
              className="upload-page__drop-icon"
            />
            <p className="upload-page__drop-title">Arrastrá tu archivo acá</p>
            <p className="upload-page__drop-sub">o usá el botón de abajo</p>
            <button
              type="button"
              className="upload-page__pick"
              aria-describedby="upload-formats-hint"
              onClick={() => inputRef.current?.click()}
            >
              Elegir archivo
            </button>
            <input
              ref={inputRef}
              type="file"
              accept={ACCEPTED_EXTENSIONS.join(",")}
              onChange={onPick}
              className="upload-page__file-input"
              aria-label="Seleccionar archivo"
            />
          </div>
        )}

        <p id="upload-formats-hint" className="upload-page__formats">
          Formatos aceptados: xlsx, csv, jpg, png, heic, pdf · Máximo 10 MB ·
          Fotos y PDFs se procesan con Google Gemini.{" "}
          <Link to="/privacy" className="upload-page__privacy-link">
            Más info
          </Link>
        </p>

        {uploading && (
          <div
            className="upload-page__status upload-page__status--processing"
            role="status"
          >
            <Loader
              size={24}
              aria-hidden="true"
              className="upload-page__spinner"
            />
            <div>
              <p className="upload-page__status-title">
                Procesando {filename}…
              </p>
              <p className="upload-page__status-sub">
                Esto puede tardar unos segundos. No cierres la página.
              </p>
            </div>
          </div>
        )}

        {error && (
          <div
            className="upload-page__status upload-page__status--error"
            role="alert"
          >
            <CircleAlert size={24} aria-hidden="true" />
            <p>{error}</p>
          </div>
        )}
      </main>
    </div>
  );
}
