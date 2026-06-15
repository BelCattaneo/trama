CREATE TABLE operation (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id           UUID NOT NULL REFERENCES node(id) ON DELETE RESTRICT,
    parse_attempt_id  UUID NOT NULL REFERENCES parse_attempt(id) ON DELETE RESTRICT,
    kind              VARCHAR(20) NOT NULL,
    operation_date    DATE NOT NULL,
    status            VARCHAR(20) NOT NULL,
    confirmed_at      TIMESTAMPTZ NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (kind IN ('order', 'offer')),
    CHECK (status IN ('confirmed')),
    UNIQUE (parse_attempt_id)
);
CREATE INDEX operation_node_id_confirmed_at_idx
    ON operation (node_id, confirmed_at DESC);

CREATE TABLE operation_line (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    operation_id  UUID NOT NULL REFERENCES operation(id) ON DELETE CASCADE,
    product       VARCHAR(200) NOT NULL,
    quantity      NUMERIC(12, 3) NOT NULL CHECK (quantity > 0),
    unit          VARCHAR(40) NULL,
    raw_text      TEXT NULL,
    line_no       SMALLINT NOT NULL,
    page          SMALLINT NULL
);
CREATE INDEX operation_line_operation_id_idx ON operation_line (operation_id);

CREATE TABLE correction (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parse_attempt_id  UUID NOT NULL REFERENCES parse_attempt(id) ON DELETE CASCADE,
    line_no           SMALLINT NULL,
    field             VARCHAR(40) NOT NULL,
    original_value    TEXT NULL,
    corrected_value   TEXT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (field IN ('product', 'quantity', 'unit', 'line_added', 'line_removed'))
);
CREATE INDEX correction_parse_attempt_id_idx ON correction (parse_attempt_id);
