CREATE TABLE IF NOT EXISTS verification_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type VARCHAR(100) NOT NULL,
    entity_id UUID NOT NULL,
    task_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    assigned_to UUID REFERENCES users(id),
    due_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT verification_tasks_status_check
        CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled'))
);

CREATE INDEX IF NOT EXISTS idx_verification_tasks_status
    ON verification_tasks (status);

CREATE INDEX IF NOT EXISTS idx_verification_tasks_assigned_to
    ON verification_tasks (assigned_to);

CREATE INDEX IF NOT EXISTS idx_verification_tasks_due_at
    ON verification_tasks (due_at);
