-- Sample SQL Queries for Federal Regulatory Layer
-- These queries demonstrate common use cases for the Prep Regulatory Engine

-- ============================================================================
-- QUERY 1: Get all certification bodies authorized for a specific scope
-- ============================================================================
-- Use case: Find all certifiers that can audit for Preventive Controls for Human Food
SELECT
    cb.name AS certifier_name,
    cb.url AS certifier_url,
    cb.email AS certifier_email,
    ab.name AS accreditor_name,
    l.recognition_expiration_date,
    l.scope_status
FROM ab_cb_scope_links l
JOIN certification_bodies cb ON cb.id = l.certification_body_id
JOIN accreditation_bodies ab ON ab.id = l.accreditation_body_id
JOIN scopes s ON s.id = l.scope_id
WHERE s.name LIKE '%Human Food%'
  AND l.scope_status = 'active'
ORDER BY l.recognition_expiration_date DESC;

-- ============================================================================
-- QUERY 2: Get all scopes a certification body is authorized for
-- ============================================================================
-- Use case: Display all certification scopes for NSF International
SELECT
    s.name AS scope_name,
    s.cfr_title_part_section,
    s.program_reference,
    ab.name AS accredited_by,
    l.recognition_initial_date,
    l.recognition_expiration_date,
    l.scope_status
FROM ab_cb_scope_links l
JOIN certification_bodies cb ON cb.id = l.certification_body_id
JOIN scopes s ON s.id = l.scope_id
JOIN accreditation_bodies ab ON ab.id = l.accreditation_body_id
WHERE cb.name = 'NSF International Strategic Registrations'
  AND l.scope_status = 'active'
ORDER BY s.name;

-- ============================================================================
-- QUERY 3: Find certifications expiring within next 6 months
-- ============================================================================
-- Use case: Proactive monitoring for expiring certifications
SELECT
    ab.name AS accreditor,
    cb.name AS certifier,
    s.name AS scope,
    l.recognition_expiration_date,
    CAST((julianday(l.recognition_expiration_date) - julianday('now')) AS INTEGER) AS days_until_expiry
FROM ab_cb_scope_links l
JOIN accreditation_bodies ab ON ab.id = l.accreditation_body_id
JOIN certification_bodies cb ON cb.id = l.certification_body_id
JOIN scopes s ON s.id = l.scope_id
WHERE l.recognition_expiration_date BETWEEN DATE('now') AND DATE('now', '+6 months')
  AND l.scope_status = 'active'
ORDER BY l.recognition_expiration_date ASC;

-- ============================================================================
-- QUERY 4: Get all certifiers with multiple scope authorizations
-- ============================================================================
-- Use case: Find versatile certification bodies that can audit multiple programs
SELECT
    cb.name AS certifier_name,
    cb.url,
    COUNT(DISTINCT l.scope_id) AS scope_count,
    GROUP_CONCAT(DISTINCT s.name, '; ') AS authorized_scopes
FROM certification_bodies cb
JOIN ab_cb_scope_links l ON l.certification_body_id = cb.id
JOIN scopes s ON s.id = l.scope_id
WHERE l.scope_status = 'active'
GROUP BY cb.id, cb.name, cb.url
HAVING COUNT(DISTINCT l.scope_id) >= 2
ORDER BY scope_count DESC, cb.name;

-- ============================================================================
-- QUERY 5: Get accreditation body statistics
-- ============================================================================
-- Use case: Dashboard summary of accreditation body coverage
SELECT
    ab.name AS accreditor,
    COUNT(DISTINCT l.certification_body_id) AS certifiers_count,
    COUNT(DISTINCT l.scope_id) AS scopes_covered,
    COUNT(l.id) AS total_authorizations
FROM accreditation_bodies ab
JOIN ab_cb_scope_links l ON l.accreditation_body_id = ab.id
WHERE l.scope_status = 'active'
GROUP BY ab.id, ab.name
ORDER BY total_authorizations DESC;

-- ============================================================================
-- QUERY 6: Find all active FSMA preventive controls certifiers
-- ============================================================================
-- Use case: Match kitchen operators to preventive controls auditors
SELECT DISTINCT
    cb.name AS certifier,
    cb.url,
    cb.email,
    s.name AS scope,
    s.cfr_title_part_section,
    l.recognition_expiration_date
FROM certification_bodies cb
JOIN ab_cb_scope_links l ON l.certification_body_id = cb.id
JOIN scopes s ON s.id = l.scope_id
WHERE (s.name LIKE '%Preventive Controls%' OR s.name LIKE '%PCHF%' OR s.name LIKE '%PCAF%')
  AND l.scope_status = 'active'
  AND l.recognition_expiration_date > DATE('now')
ORDER BY cb.name, s.name;

-- ============================================================================
-- QUERY 7: Get certification bodies by accreditor with expiration dates
-- ============================================================================
-- Use case: Audit trail for specific accreditation body
SELECT
    ab.name AS accreditor,
    cb.name AS certifier,
    s.name AS scope,
    l.recognition_initial_date,
    l.recognition_expiration_date,
    CASE
        WHEN l.recognition_expiration_date < DATE('now') THEN 'EXPIRED'
        WHEN l.recognition_expiration_date < DATE('now', '+90 days') THEN 'EXPIRING_SOON'
        ELSE 'VALID'
    END AS validity_status
FROM ab_cb_scope_links l
JOIN accreditation_bodies ab ON ab.id = l.accreditation_body_id
JOIN certification_bodies cb ON cb.id = l.certification_body_id
JOIN scopes s ON s.id = l.scope_id
WHERE ab.name = 'ANSI National Accreditation Board (ANAB)'
ORDER BY l.recognition_expiration_date ASC;

-- ============================================================================
-- QUERY 8: Get all scopes with their regulatory anchors
-- ============================================================================
-- Use case: Display complete scope catalog with CFR citations
SELECT
    s.id,
    s.name AS scope_name,
    s.cfr_title_part_section,
    s.program_reference,
    s.notes,
    COUNT(DISTINCT l.certification_body_id) AS authorized_certifiers
FROM scopes s
LEFT JOIN ab_cb_scope_links l ON l.scope_id = s.id AND l.scope_status = 'active'
GROUP BY s.id, s.name, s.cfr_title_part_section, s.program_reference, s.notes
ORDER BY s.id;

-- ============================================================================
-- QUERY 9: Find certifiers authorized for produce safety
-- ============================================================================
-- Use case: Match produce handlers/packers to authorized auditors
SELECT
    cb.name AS certifier_name,
    cb.url,
    cb.email,
    ab.name AS accredited_by,
    l.recognition_expiration_date,
    CAST((julianday(l.recognition_expiration_date) - julianday('now')) AS INTEGER) AS days_remaining
FROM ab_cb_scope_links l
JOIN certification_bodies cb ON cb.id = l.certification_body_id
JOIN accreditation_bodies ab ON ab.id = l.accreditation_body_id
JOIN scopes s ON s.id = l.scope_id
WHERE s.name LIKE '%Produce Safety%'
  AND l.scope_status = 'active'
  AND l.recognition_expiration_date > DATE('now')
ORDER BY cb.name;

-- ============================================================================
-- QUERY 10: Upcoming expirations in next 18 months
-- ============================================================================
-- Use case: Long-term planning for re-accreditation monitoring
SELECT
    ab.name AS accreditor,
    cb.name AS certifier,
    s.name AS scope,
    l.recognition_expiration_date,
    CAST((julianday(l.recognition_expiration_date) - julianday('now')) AS INTEGER) AS days_until_expiry,
    CASE
        WHEN julianday(l.recognition_expiration_date) - julianday('now') <= 90 THEN 'CRITICAL'
        WHEN julianday(l.recognition_expiration_date) - julianday('now') <= 180 THEN 'HIGH'
        WHEN julianday(l.recognition_expiration_date) - julianday('now') <= 365 THEN 'MEDIUM'
        ELSE 'LOW'
    END AS priority
FROM ab_cb_scope_links l
JOIN accreditation_bodies ab ON ab.id = l.accreditation_body_id
JOIN certification_bodies cb ON cb.id = l.certification_body_id
JOIN scopes s ON s.id = l.scope_id
WHERE l.recognition_expiration_date BETWEEN DATE('now') AND DATE('now', '+18 months')
  AND l.scope_status = 'active'
ORDER BY l.recognition_expiration_date ASC;

-- ============================================================================
-- QUERY 11: Certifier search with contact information
-- ============================================================================
-- Use case: API endpoint for certifier lookup by partial name match
SELECT
    cb.id,
    cb.name,
    cb.url,
    cb.email,
    GROUP_CONCAT(DISTINCT s.name, ' | ') AS scopes,
    MIN(l.recognition_expiration_date) AS earliest_expiration
FROM certification_bodies cb
JOIN ab_cb_scope_links l ON l.certification_body_id = cb.id
JOIN scopes s ON s.id = l.scope_id
WHERE l.scope_status = 'active'
  AND cb.name LIKE '%NSF%'
GROUP BY cb.id, cb.name, cb.url, cb.email;

-- ============================================================================
-- QUERY 12: Full authority chain for a specific facility certification
-- ============================================================================
-- Use case: Compliance verification - trace certification legitimacy
-- Replace 'NSF International Strategic Registrations' with the certifier
-- and 'Preventive Controls for Human Food' with the scope
SELECT
    'FDA' AS federal_authority,
    ab.name AS accreditation_body,
    ab.url AS ab_url,
    cb.name AS certification_body,
    cb.url AS cb_url,
    s.name AS scope,
    s.cfr_title_part_section AS legal_basis,
    l.recognition_initial_date,
    l.recognition_expiration_date,
    l.scope_status,
    CASE
        WHEN l.recognition_expiration_date >= DATE('now') AND l.scope_status = 'active' THEN 'VALID'
        ELSE 'INVALID'
    END AS chain_validity
FROM ab_cb_scope_links l
JOIN accreditation_bodies ab ON ab.id = l.accreditation_body_id
JOIN certification_bodies cb ON cb.id = l.certification_body_id
JOIN scopes s ON s.id = l.scope_id
WHERE cb.name = 'NSF International Strategic Registrations'
  AND s.name LIKE '%Human Food%'
ORDER BY l.recognition_expiration_date DESC
LIMIT 1;
