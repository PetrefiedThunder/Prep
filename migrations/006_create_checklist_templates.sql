CREATE TABLE IF NOT EXISTS checklist_templates (
    id UUID PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    version INTEGER NOT NULL,
    schema JSONB NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_checklist_template_name_version
    ON checklist_templates (name, version);
