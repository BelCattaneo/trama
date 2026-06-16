ALTER TABLE operation
    ADD COLUMN supplier_node_id UUID NULL
    REFERENCES node(id) ON DELETE SET NULL;

CREATE INDEX operation_supplier_node_id_idx
    ON operation (supplier_node_id);
