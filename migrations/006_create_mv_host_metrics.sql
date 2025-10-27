-- Migration: Create mv_host_metrics materialized view for analytics API
-- Version: 006
-- Date: 2025-02-14

BEGIN;

-- Drop the materialized view if it already exists so the definition can be replaced.
DROP MATERIALIZED VIEW IF EXISTS mv_host_metrics;

CREATE MATERIALIZED VIEW mv_host_metrics AS
WITH hosts AS (
    SELECT DISTINCT k.host_id
    FROM kitchens k
    WHERE k.host_id IS NOT NULL
),
recent_bookings AS (
    SELECT
        k.host_id,
        COALESCE(SUM(b.total_amount), 0)::numeric(14, 2) AS revenue_last_30,
        COUNT(*) AS shifts_30
    FROM bookings b
    JOIN kitchens k ON k.id = b.kitchen_id
    WHERE b.status = 'completed'
      AND b.end_time >= NOW() - INTERVAL '30 days'
    GROUP BY k.host_id
),
recent_incidents AS (
    SELECT
        hi.host_id,
        COUNT(*) AS incidents_30
    FROM host_incidents hi
    WHERE hi.occurred_at >= NOW() - INTERVAL '30 days'
    GROUP BY hi.host_id
)
SELECT
    h.host_id,
    COALESCE(rb.revenue_last_30, 0)::numeric(14, 2) AS revenue_last_30,
    COALESCE(rb.shifts_30, 0) AS shifts_30,
    CASE
        WHEN COALESCE(rb.shifts_30, 0) = 0 THEN 0::numeric
        ELSE ROUND(COALESCE(ri.incidents_30, 0)::numeric / rb.shifts_30, 4)
    END AS incident_rate,
    NOW() AS calculated_at
FROM hosts h
LEFT JOIN recent_bookings rb ON h.host_id = rb.host_id
LEFT JOIN recent_incidents ri ON h.host_id = ri.host_id
WITH NO DATA;

-- Indexes to support the analytics API use cases.
CREATE UNIQUE INDEX idx_mv_host_metrics_host_id ON mv_host_metrics (host_id);
CREATE INDEX idx_mv_host_metrics_revenue_last_30 ON mv_host_metrics (revenue_last_30 DESC);
CREATE INDEX idx_mv_host_metrics_incident_rate ON mv_host_metrics (incident_rate);

COMMIT;
