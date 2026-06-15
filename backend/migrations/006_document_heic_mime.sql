-- E5 added image/heic and image/heif to the LLM dispatch path, but the CHECK on
-- document.mime_type still rejects them; every HEIC upload would fail at INSERT.

ALTER TABLE document DROP CONSTRAINT document_mime_type_check;
ALTER TABLE document ADD CONSTRAINT document_mime_type_check CHECK (
    mime_type IN (
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'text/csv',
        'image/jpeg',
        'image/png',
        'image/heic',
        'image/heif',
        'application/pdf'
    )
);
