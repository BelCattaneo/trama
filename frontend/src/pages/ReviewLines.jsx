import { Plus, Trash2 } from "lucide-react";

const UNREADABLE = "unreadable";

function isUnreadable(line) {
  return line.product === UNREADABLE;
}

function lineId(line) {
  return line.line_no !== null ? line.line_no : line._clientId;
}

function lineKey(line) {
  return line.line_no !== null ? `o-${line.line_no}` : `c-${line._clientId}`;
}

export default function ReviewLines({
  lines,
  readOnly,
  onUpdate,
  onRemove,
  onAdd,
  groupByPage,
}) {
  if (lines.length === 0) {
    return (
      <section className="review-page__lines">
        <p className="review-page__lines-empty">
          {readOnly
            ? "No hay líneas en este documento."
            : "No hay líneas todavía. Agregá la primera con el botón de abajo."}
        </p>
        {!readOnly && (
          <button
            type="button"
            className="review-page__add-line"
            onClick={onAdd}
          >
            <Plus size={16} aria-hidden="true" />
            Agregar línea
          </button>
        )}
      </section>
    );
  }

  if (groupByPage) {
    const grouped = new Map();
    for (const line of lines) {
      const key = line.page ?? 0;
      if (!grouped.has(key)) grouped.set(key, []);
      grouped.get(key).push(line);
    }
    const pages = [...grouped.keys()].sort((a, b) => a - b);
    return (
      <section className="review-page__lines">
        {pages.map((page) => (
          <div key={page} className="review-page__lines-group">
            <h3 className="review-page__lines-group-title">
              {page ? `Página ${page}` : "Sin página"}
            </h3>
            <LineList
              lines={grouped.get(page)}
              readOnly={readOnly}
              onUpdate={onUpdate}
              onRemove={onRemove}
            />
          </div>
        ))}
        {!readOnly && (
          <button
            type="button"
            className="review-page__add-line"
            onClick={onAdd}
          >
            <Plus size={16} aria-hidden="true" />
            Agregar línea
          </button>
        )}
      </section>
    );
  }

  return (
    <section className="review-page__lines">
      <LineList
        lines={lines}
        readOnly={readOnly}
        onUpdate={onUpdate}
        onRemove={onRemove}
      />
      {!readOnly && (
        <button type="button" className="review-page__add-line" onClick={onAdd}>
          <Plus size={16} aria-hidden="true" />
          Agregar línea
        </button>
      )}
    </section>
  );
}

function LineList({ lines, readOnly, onUpdate, onRemove }) {
  return (
    <ul className="review-page__line-list">
      {lines.map((line) => (
        <LineRow
          key={lineKey(line)}
          line={line}
          readOnly={readOnly}
          onUpdate={onUpdate}
          onRemove={onRemove}
        />
      ))}
    </ul>
  );
}

function LineRow({ line, readOnly, onUpdate, onRemove }) {
  const productUnreadable = isUnreadable(line);
  const quantityMissing = line.quantity === 0;
  const highlighted = productUnreadable || quantityMissing;
  const id = lineId(line);
  return (
    <li
      className={
        highlighted
          ? "review-page__line review-page__line--warn"
          : "review-page__line"
      }
      data-warn={highlighted ? "true" : "false"}
    >
      <div className="review-page__line-field">
        <label
          className="review-page__line-label"
          htmlFor={`line-${id}-product`}
        >
          Producto
        </label>
        <input
          id={`line-${id}-product`}
          className="review-page__line-input"
          value={productUnreadable ? "" : line.product}
          placeholder={productUnreadable ? "completar acá" : ""}
          onChange={(event) => onUpdate(id, "product", event.target.value)}
          readOnly={readOnly}
          disabled={readOnly}
        />
      </div>
      <div className="review-page__line-field">
        <label
          className="review-page__line-label"
          htmlFor={`line-${id}-quantity`}
        >
          Cantidad
        </label>
        <input
          id={`line-${id}-quantity`}
          className="review-page__line-input"
          type="number"
          step="any"
          value={quantityMissing ? "" : line.quantity}
          placeholder={quantityMissing ? "completar acá" : ""}
          onChange={(event) => onUpdate(id, "quantity", event.target.value)}
          readOnly={readOnly}
          disabled={readOnly}
        />
      </div>
      <div className="review-page__line-field">
        <label className="review-page__line-label" htmlFor={`line-${id}-unit`}>
          Unidad
        </label>
        <input
          id={`line-${id}-unit`}
          className="review-page__line-input"
          value={line.unit ?? ""}
          onChange={(event) => onUpdate(id, "unit", event.target.value)}
          readOnly={readOnly}
          disabled={readOnly}
        />
      </div>
      {!readOnly && (
        <button
          type="button"
          className="review-page__line-remove"
          onClick={() => onRemove(id)}
          aria-label="Eliminar línea"
        >
          <Trash2 size={16} aria-hidden="true" />
          Eliminar
        </button>
      )}
    </li>
  );
}
