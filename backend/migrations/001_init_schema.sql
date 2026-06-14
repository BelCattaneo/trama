CREATE TABLE node (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cuit          VARCHAR(13) UNIQUE NOT NULL,
    display_name  VARCHAR(120) NOT NULL,
    role          VARCHAR(20) NOT NULL CHECK (role IN ('consumer', 'producer', 'both')),
    address_text  VARCHAR(300),
    latitude      DOUBLE PRECISION NOT NULL,
    longitude     DOUBLE PRECISION NOT NULL,
    zone_label    VARCHAR(120),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX node_role_idx ON node (role);

CREATE TABLE app_user (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id        UUID NOT NULL REFERENCES node(id) ON DELETE RESTRICT,
    email          VARCHAR(254) UNIQUE NOT NULL,
    password_hash  VARCHAR(255) NOT NULL,
    full_name      VARCHAR(120),
    last_login_at  TIMESTAMPTZ,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX app_user_node_id_idx ON app_user (node_id);
