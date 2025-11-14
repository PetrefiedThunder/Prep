# Federal Regulatory Layer - Data Package

## Overview

This directory contains the **federal compliance backbone** for the Prep Regulatory Engine. It encodes the authority chain from FDA oversight down to on-the-ground certification for food safety programs under FSMA (Food Safety Modernization Act).

## Directory Contents

### Core Data Files

| File | Description |
|------|-------------|
| `prep_federal_layer.sqlite` | SQLite database with all federal regulatory data |
| `prep_federal_certifiers_normalized.csv` | Master denormalized dataset (unified source of truth) |
| `ab_table.csv` | Accreditation bodies reference table |
| `certification_bodies.csv` | Certification bodies reference table |
| `scopes.csv` | Food safety scopes reference table |
| `accreditor_certifier_scope_links.csv` | Relationship mapping (AB → CB → Scope) |
| `scope_to_regulatory_anchor_scaffold.csv` | CFR citations and regulatory anchors |

### Schema & Validation

| File | Description |
|------|-------------|
| `accreditation_body.schema.json` | JSON schema for accreditation body validation |
| `certification_body.schema.json` | JSON schema for certification body validation |
| `scope.schema.json` | JSON schema for scope validation |
| `scope_link.schema.json` | JSON schema for scope link validation |

### Documentation

| File | Description |
|------|-------------|
| `prep_federal_layer_data_dictionary.md` | Complete data dictionary with field definitions |
| `prep_federal_layer_sample_queries.sql` | Sample SQL queries for common use cases |
| `README.md` | This file |

### Utilities

| File | Description |
|------|-------------|
| `create_database.py` | Script to generate SQLite database from CSV files |

## Quick Start

### 1. Verify Database

```bash
sqlite3 prep_federal_layer.sqlite "SELECT COUNT(*) FROM scopes;"
```

Expected output: `8` (8 food safety scopes)

### 2. Query Certifiers

```bash
sqlite3 prep_federal_layer.sqlite << EOF
SELECT cb.name, s.name AS scope
FROM certification_bodies cb
JOIN ab_cb_scope_links l ON l.certification_body_id = cb.id
JOIN scopes s ON s.id = l.scope_id
WHERE s.name LIKE '%Human Food%'
LIMIT 5;
EOF
```

### 3. Check Expirations

```bash
sqlite3 prep_federal_layer.sqlite << EOF
SELECT cb.name, s.name, l.recognition_expiration_date
FROM ab_cb_scope_links l
JOIN certification_bodies cb ON cb.id = l.certification_body_id
JOIN scopes s ON s.id = l.scope_id
WHERE l.recognition_expiration_date < DATE('now', '+180 days')
ORDER BY l.recognition_expiration_date;
EOF
```

## Data Model

### Entity Relationship

```
┌─────────────────────────┐
│  accreditation_bodies   │
│  - id (PK)             │
│  - name                │
│  - url                 │
│  - email               │
│  - contact             │
└──────────┬──────────────┘
           │
           │ 1:N
           │
┌──────────▼──────────────┐
│  ab_cb_scope_links      │
│  - id (PK)             │
│  - accreditation_body_id│ (FK)
│  - certification_body_id│ (FK)
│  - scope_id            │ (FK)
│  - recognition_initial_date
│  - recognition_expiration_date
│  - scope_status        │
│  - source              │
└──────┬────────┬─────────┘
       │        │
       │ N:1    │ N:1
       │        │
┌──────▼───────────┐  ┌──────▼───────┐
│certification_    │  │   scopes     │
│bodies            │  │   - id (PK)  │
│  - id (PK)      │  │   - name     │
│  - name         │  │   - cfr_*    │
│  - url          │  │   - program  │
│  - email        │  │   - notes    │
└──────────────────┘  └──────────────┘
```

### Tables

1. **accreditation_bodies**: 2 records (ANAB, IAS)
2. **certification_bodies**: 15 records (NSF, SAI Global, SCS, etc.)
3. **scopes**: 8 records (PCHF, PCAF, Produce Safety, etc.)
4. **ab_cb_scope_links**: 34 records (authorization relationships)

## Food Safety Scopes

| ID | Scope | CFR Citation |
|----|-------|--------------|
| 1 | Preventive Controls for Human Food (PCHF) | 21 CFR 117 |
| 2 | Preventive Controls for Animal Food (PCAF) | 21 CFR 507 |
| 3 | Produce Safety | 21 CFR 112 |
| 4 | Seafood HACCP | 21 CFR 123 |
| 5 | Juice HACCP | 21 CFR 120 |
| 6 | Low-Acid Canned Foods (LACF) | 21 CFR 113 |
| 7 | Acidified Foods | 21 CFR 114 |
| 8 | Infant Formula | 21 CFR 106 and 107 |

## Accreditation Bodies

| ID | Name | Website |
|----|------|---------|
| 1 | ANSI National Accreditation Board (ANAB) | https://anab.ansi.org |
| 2 | International Accreditation Service (IAS) | https://www.iasonline.org |

## Usage Examples

### Python Integration

```python
import sqlite3

# Connect to database
conn = sqlite3.connect('prep_federal_layer.sqlite')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Find certifiers for PCHF
cursor.execute("""
    SELECT cb.name, cb.email, l.recognition_expiration_date
    FROM certification_bodies cb
    JOIN ab_cb_scope_links l ON l.certification_body_id = cb.id
    JOIN scopes s ON s.id = l.scope_id
    WHERE s.name LIKE '%Human Food%'
      AND l.scope_status = 'active'
""")

for row in cursor.fetchall():
    print(f"{row['name']}: expires {row['recognition_expiration_date']}")

conn.close()
```

### API Integration

The Federal Regulatory Service provides REST API access:

```bash
# Get all scopes
curl http://localhost:8001/federal/scopes

# Find certifiers for produce safety
curl "http://localhost:8001/federal/certifiers?scope=Produce"

# Check expirations
curl "http://localhost:8001/federal/expiring?days=180"
```

## Data Refresh

### Manual Refresh

To rebuild the database from CSV files:

```bash
python create_database.py
```

### Automated ETL

The Federal Regulatory Service includes an ETL pipeline:

```bash
cd ../../apps/federal_regulatory_service
python etl.py
```

### Update Frequency

Recommended update schedule:
- **Weekly**: Check for new certifications or status changes
- **Monthly**: Validate expiration dates
- **Quarterly**: Full reconciliation with FDA's official listings

## Data Sources

- **ANAB Directory**: https://anab.ansi.org (Third-Party Certification Bodies)
- **IAS Directory**: https://www.iasonline.org (Food Safety Accreditation)
- **FDA Listings**: FDA Third-Party Certification Program Official Registry

## Validation

### Data Integrity Checks

```sql
-- Check for orphaned links
SELECT COUNT(*) FROM ab_cb_scope_links l
LEFT JOIN accreditation_bodies ab ON ab.id = l.accreditation_body_id
WHERE ab.id IS NULL;

-- Check expired active certifications
SELECT COUNT(*) FROM ab_cb_scope_links
WHERE scope_status = 'active'
  AND recognition_expiration_date < DATE('now');

-- Verify all scopes have CFR citations
SELECT COUNT(*) FROM scopes
WHERE cfr_title_part_section IS NULL OR cfr_title_part_section = '';
```

### Schema Validation

```bash
# Validate JSON against schemas (requires jsonschema)
python -m jsonschema -i ab_table.csv accreditation_body.schema.json
```

## Integration Points

### With Prep Compliance Service

The federal layer integrates with:

1. **Kitchen onboarding**: Match facility activities to required scopes
2. **Certifier selection**: Show authorized certifiers for facility type
3. **Compliance validation**: Verify certifier authority chain
4. **Expiration monitoring**: Alert when certifications need renewal

### With State/Local Data

Link federal scopes to:

- State health department permits
- County inspection records
- Local jurisdiction requirements

### Graph Database

Transform to graph for advanced queries:

```cypher
// Neo4j example
MATCH (ab:AccreditationBody)-[:ACCREDITS]->(cb:CertificationBody)
      -[:AUTHORIZED_FOR]->(s:Scope)
WHERE s.name CONTAINS 'Human Food'
RETURN ab, cb, s
```

## Maintenance

### Adding New Certifiers

1. Update `certification_bodies.csv` with new entry
2. Add authorization records to `accreditor_certifier_scope_links.csv`
3. Regenerate database: `python create_database.py`
4. Update normalized file: `prep_federal_certifiers_normalized.csv`

### Updating Expiration Dates

1. Edit `accreditor_certifier_scope_links.csv`
2. Update `recognition_expiration_date` field
3. Regenerate database

### Adding New Scopes

1. Add entry to `scopes.csv` with CFR citation
2. Update `scope_to_regulatory_anchor_scaffold.csv`
3. Regenerate database

## Troubleshooting

### Database Locked

```bash
# Close all connections and rebuild
rm prep_federal_layer.sqlite
python create_database.py
```

### Missing Data

```bash
# Verify CSV files exist
ls -lh *.csv

# Check record counts
wc -l *.csv
```

### Schema Errors

```bash
# Validate CSV format
csvlint certification_bodies.csv
```

## Support

For questions or issues:
- **Technical**: See `/apps/federal_regulatory_service/README.md`
- **Data accuracy**: Consult FDA official listings
- **Regulatory**: Contact legal counsel or FDA guidance

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-10-30 | Initial release with 2 ABs, 15 CBs, 8 scopes, 34 links |

## License

See main repository LICENSE file.
