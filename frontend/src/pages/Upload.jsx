import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CircleAlert, Loader, Upload as UploadIcon } from "lucide-react";
import NavBarAuth from "../components/NavBarAuth";
import { apiPostForm } from "../lib/api";
import "./Upload.css";

const MAX_BYTES = 10 * 1024 * 1024;
const ACCEPTED_EXTENSIONS = [".xlsx", ".csv", ".jpg", ".jpeg", ".png", ".pdf"];
const ACCEPTED_MIMES = new Set([
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "text/csv",
  "image/jpeg",
  "image/png",
  "application/pdf",
]);

function isAcceptedFile(file) {
  if (ACCEPTED_MIMES.has(file.type)) return true;
  const name = file.name.toLowerCase();
  return ACCEPTED_EXTENSIONS.some((ext) => name.endsWith(ext));
}

export default function Upload() {
  const navigate = useNavigate();
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [filename, setFilename] = useState("");
  const [error, setError] = useState("");

  async function handleFile(file) {
    setError("");
    if (!isAcceptedFile(file)) {
      setError("Formato no soportado. Aceptamos xlsx, csv, jpg, png o pdf.");
      return;
    }
    if (file.size > MAX_BYTES) {
      setError("El archivo es muy grande. Máximo 10 MB.");
      return;
    }
    setFilename(file.name);
    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const response = await apiPostForm("/api/documents", formData);
      if (response.status === 201) {
        navigate("/mis-documentos");
        return;
      }
      if (response.status === 400) {
        const body = await response.json().catch(() => ({}));
        setError(body.error || "El archivo no pudo ser procesado.");
      } else if (response.status === 401) {
        setError("Tu sesión expiró. Iniciá sesión de nuevo.");
      } else {
        setError("No pudimos subir el archivo, intentá de nuevo.");
      }
    } catch {
      setError("No pudimos subir el archivo, intentá de nuevo.");
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
        <h1 className="upload-page__title">Subir pedido</h1>
        <p className="upload-page__lead">
          Subí tu planilla, foto o PDF con el pedido. Trama se encarga de
          interpretarlo.
        </p>

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
            <UploadIcon size={40} aria-hidden="true" />
            <p className="upload-page__drop-title">Arrastrá tu archivo acá</p>
            <p className="upload-page__drop-sub">o usá el botón de abajo</p>
            <button
              type="button"
              className="upload-page__pick"
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

        <p className="upload-page__formats">
          Formatos aceptados: xlsx, csv, jpg, png, pdf · Máximo 10 MB
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
