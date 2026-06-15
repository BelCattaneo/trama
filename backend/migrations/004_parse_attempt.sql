CREATE TABLE parse_attempt (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     UUID NOT NULL REFERENCES document(id) ON DELETE CASCADE,
    strategy        VARCHAR(20) NOT NULL,
    confidence      REAL NULL,
    payload         JSONB NULL,
    prompt_version  VARCHAR(40) NULL,
    error_message   TEXT NULL,
    is_winner       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (strategy IN ('deterministic', 'llm')),
    CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1))
);
CREATE INDEX parse_attempt_document_id_idx ON parse_attempt (document_id);
CREATE UNIQUE INDEX parse_attempt_winner_unique
    ON parse_attempt (document_id) WHERE is_winner;
