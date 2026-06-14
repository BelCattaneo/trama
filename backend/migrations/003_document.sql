CREATE TABLE document (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id           UUID NOT NULL REFERENCES node(id) ON DELETE CASCADE,
    original_filename VARCHAR(255) NOT NULL,
    mime_type         VARCHAR(100) NOT NULL,
    size_bytes        INTEGER NOT NULL CHECK (size_bytes > 0),
    content_hash      CHAR(64) NOT NULL,
    storage_ref       VARCHAR(500) NOT NULL,
    uploaded_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (mime_type IN (
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'text/csv',
        'image/jpeg',
        'image/png',
        'application/pdf'
    ))
);
CREATE INDEX document_node_id_idx ON document (node_id);
CREATE INDEX document_content_hash_idx ON document (content_hash);
