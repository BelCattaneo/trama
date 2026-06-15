import { useEffect, useRef, useState } from "react";
import { Loader } from "lucide-react";

const IMAGE_TYPES = new Set(["image/jpeg", "image/png"]);
const HEIC_TYPES = new Set(["image/heic", "image/heif"]);
const SPREADSHEET_TYPES = new Set([
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "text/csv",
]);

export default function ReviewPreview({ document, activePage }) {
  const fileUrl = `/api/documents/${document.id}/file`;

  if (IMAGE_TYPES.has(document.mime_type)) {
    return (
      <img
        src={fileUrl}
        alt={document.original_filename}
        className="review-page__preview-image"
      />
    );
  }

  if (HEIC_TYPES.has(document.mime_type)) {
    return <HeicPreview src={fileUrl} alt={document.original_filename} />;
  }

  if (document.mime_type === "application/pdf") {
    return <PdfPreview src={fileUrl} activePage={activePage} />;
  }

  if (SPREADSHEET_TYPES.has(document.mime_type)) {
    return (
      <div className="review-page__preview-spreadsheet">
        <p>No mostramos planillas en pantalla.</p>
        <a
          href={fileUrl}
          download={document.original_filename}
          className="review-page__download"
        >
          Descargar original
        </a>
      </div>
    );
  }

  return (
    <div className="review-page__preview-unknown">
      <a
        href={fileUrl}
        download={document.original_filename}
        className="review-page__download"
      >
        Descargar original
      </a>
    </div>
  );
}

function HeicPreview({ src, alt }) {
  const [state, setState] = useState({ status: "loading", url: null });

  useEffect(() => {
    let cancelled = false;
    let createdUrl = null;
    (async () => {
      const response = await fetch(src, { credentials: "include" });
      const heicBlob = await response.blob();
      const { default: heic2any } = await import("heic2any");
      const jpegBlob = await heic2any({ blob: heicBlob, toType: "image/jpeg" });
      if (cancelled) return;
      createdUrl = URL.createObjectURL(jpegBlob);
      setState({ status: "ready", url: createdUrl });
    })().catch(() => {
      if (!cancelled) setState({ status: "error", url: null });
    });
    return () => {
      cancelled = true;
      if (createdUrl) URL.revokeObjectURL(createdUrl);
    };
  }, [src]);

  if (state.status === "loading") {
    return (
      <div className="review-page__preview-loading" role="status">
        <Loader size={24} aria-hidden="true" />
        <span>Decodificando imagen…</span>
      </div>
    );
  }
  if (state.status === "error") {
    return (
      <div className="review-page__preview-error" role="alert">
        No pudimos mostrar la imagen.
      </div>
    );
  }
  return (
    <img src={state.url} alt={alt} className="review-page__preview-image" />
  );
}

function PdfPreview({ src, activePage }) {
  const canvasRef = useRef(null);
  const [state, setState] = useState({ status: "loading", numPages: 0 });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const pdfjs = await import("pdfjs-dist");
      const worker = await import("pdfjs-dist/build/pdf.worker.mjs?url");
      pdfjs.GlobalWorkerOptions.workerSrc = worker.default;
      const response = await fetch(src, { credentials: "include" });
      const data = await response.arrayBuffer();
      const doc = await pdfjs.getDocument({ data }).promise;
      if (cancelled) return;
      const pageNumber = activePage || 1;
      const page = await doc.getPage(pageNumber);
      const viewport = page.getViewport({ scale: 1.2 });
      const canvas = canvasRef.current;
      if (!canvas || cancelled) return;
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      const ctx = canvas.getContext("2d");
      await page.render({ canvasContext: ctx, viewport }).promise;
      if (!cancelled) {
        setState({ status: "ready", numPages: doc.numPages });
      }
    })().catch(() => {
      if (!cancelled) setState({ status: "error", numPages: 0 });
    });
    return () => {
      cancelled = true;
    };
  }, [src, activePage]);

  if (state.status === "error") {
    return (
      <div className="review-page__preview-error" role="alert">
        No pudimos mostrar el PDF.
      </div>
    );
  }
  return (
    <div className="review-page__preview-pdf">
      {state.status === "loading" && (
        <div className="review-page__preview-loading" role="status">
          <Loader size={24} aria-hidden="true" />
          <span>Cargando PDF…</span>
        </div>
      )}
      <canvas ref={canvasRef} className="review-page__preview-canvas" />
    </div>
  );
}
