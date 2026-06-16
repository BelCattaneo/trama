import NavBarPublic from "../components/NavBarPublic";
import "./Privacy.css";

export default function Privacy() {
  return (
    <div className="page-shell privacy-page">
      <NavBarPublic />
      <main className="privacy-page__content">
        <h1 className="privacy-page__title">Privacidad</h1>
        <p className="privacy-page__lead">
          Este documento describe qué datos manejamos en trama, con quién los
          compartimos y qué derechos tenés.
        </p>
        <p>
          trama todavía está en desarrollo. Si algo no te cierra, escribinos
          antes de subir información sensible.
        </p>

        <h2>Qué datos recolectamos</h2>
        <ul>
          <li>
            <strong>Datos de registro</strong>: email, CUIT, dirección y nombre
            del nodo (cooperativa, mutual, organización).
          </li>
          <li>
            <strong>Archivos que subís</strong>: planillas (xlsx, csv), fotos
            (jpg, png, heic) o PDFs con tu oferta semanal o lista de pedidos.
          </li>
          <li>
            <strong>Datos parseados</strong>: las líneas que extraemos de cada
            archivo (producto, cantidad, unidad), más la confirmación humana que
            hacés en pantalla antes de persistir.
          </li>
        </ul>

        <h2>Con quién los compartimos</h2>
        <p>
          trama usa un parser híbrido. El camino del archivo depende del
          formato:
        </p>
        <ul>
          <li>
            <strong>xlsx y csv</strong> se procesan <strong>localmente</strong>{" "}
            en nuestro backend. No se envían a terceros.
          </li>
          <li>
            <strong>Fotos (jpg, png, heic, heif) y PDFs</strong> se envían a{" "}
            <strong>Google Gemini</strong> (API de IA de Google) para extraer el
            contenido tabular. Esto incluye los bytes completos del archivo si
            tu foto tiene anotaciones a mano, precios, firmas o nombres, todo
            eso viaja a Google junto con la planilla.
          </li>
        </ul>
        <p>
          Usamos el LLM como <strong>fallback</strong>, no como primera opción.
          Si podés subir una planilla digital (xlsx, csv) en vez de una foto,
          evitás el paso por Google.
        </p>

        <h2>Por qué pasamos las fotos por un LLM</h2>
        <p>
          Muchxs productorxs trabajan con planillas en cuaderno, fotos de
          WhatsApp o PDFs escaneados. Forzar a digitalizar antes de usar trama
          dejaría afuera justo a las personas que más necesitan la herramienta.
          El LLM es lo que permite que esos formatos también funcionen.
        </p>

        <h2>Qué guarda Google</h2>
        <p>
          Google Gemini se rige por sus propios términos para el uso de la API.
          Recomendamos leer:
        </p>
        <ul>
          <li>
            <a
              href="https://ai.google.dev/gemini-api/terms"
              target="_blank"
              rel="noopener noreferrer"
            >
              Términos de servicio de Gemini API
            </a>
          </li>
        </ul>
        <p>
          En particular, los términos describen si Google retiene los archivos,
          por cuánto tiempo y bajo qué condiciones puede usarlos para mejorar el
          modelo. Esos términos pueden cambiar y no dependen de trama.
        </p>

        <h2>Qué guarda trama</h2>
        <ul>
          <li>
            El <strong>archivo crudo</strong> que subiste, en almacenamiento
            local del backend.
          </li>
          <li>
            El <strong>texto parseado</strong> por el deterministic parser o por
            el LLM, incluyendo la transcripción cruda de cada fila (
            <code>parse_attempt.payload</code>). Esto puede incluir precios o
            anotaciones que estaban en la planilla original.
          </li>
          <li>
            Tu <strong>confirmación humana</strong> sobre las líneas finales
            antes de persistir.
          </li>
        </ul>
        <p>
          trama <strong>nunca vende datos a terceros</strong>. No los exponemos
          en logs públicos, endpoints abiertos ni mensajes de error.
        </p>
        <p>
          Los precios y montos individuales se guardan en <code>null</code> por
          defecto. Cualquier opt-in para activarlos requiere acuerdo explícito
          del colectivo dueño de los datos.
        </p>

        <h2>Tus derechos</h2>
        <p>Podés pedirnos:</p>
        <ul>
          <li>
            Eliminar tu cuenta y todos los datos asociados (archivos, parseos,
            operaciones).
          </li>
          <li>Exportar lo que tenemos sobre tu nodo.</li>
          <li>Corregir cualquier dato mal cargado.</li>
        </ul>
        <p>
          Para cualquiera de estos pedidos, escribinos a{" "}
          <strong>[admin contact placeholder]</strong>.
        </p>

        <h2>Cambios a esta política</h2>
        <p>
          Si cambia el flujo de datos, actualizamos este documento y avisamos en
          la pantalla de carga.
        </p>
      </main>
    </div>
  );
}
