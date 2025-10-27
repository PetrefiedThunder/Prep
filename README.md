# Prep

## Overview
This repository hosts early prototypes for the Prep accessibility platform and related compliance tooling. It aggregates several experimental modules and service stubs that explore accessibility, financial, and regulatory workflows.

## Installation
1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd Prep
   ```
2. (Optional) Create a virtual environment for Python components:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. Install Python dependencies defined in `pyproject.toml`:
   ```bash
   pip install -e .
   ```
4. For the `prepchef` subproject, ensure Node.js is installed and run:
   ```bash
   npm install
   ```

### Optional tools
- Install [Ruff](https://docs.astral.sh/ruff/) to lint Python modules quickly:
  ```bash
  ruff check .
  ```
- Install [Prettier](https://prettier.io/) if you plan to modify the TypeScript or frontend code:
  ```bash
  npm install --global prettier
  ```

## Testing
Run the test suite with:
```bash
pytest
```

For TypeScript or frontend changes, run the accompanying checks from the repository root:
```bash
npm run lint
npm run test
```

## Database migrations

### Host metrics materialized view
The analytics API expects the `mv_host_metrics` materialized view to be present and populated. To provision or update the view:

1. Apply the migration:
   ```bash
   psql $DATABASE_URL <<'SQL'
   \i migrations/006_create_mv_host_metrics.sql
   SQL
   ```
   Replace `$DATABASE_URL` with the connection string for the target environment.
2. Populate the view using the provided helper script (required because the migration creates the view with `WITH NO DATA`):
   ```bash
   python scripts/refresh_views.py
   ```
   The script respects standard `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME` environment variables, or you can supply a full DSN via `--dsn`.

Include both steps in your deployment pipeline so new environments expose consistent analytics results.

## Submodules
- `auto_projection_bot/` – Generates automated financial projections.  
- `dol_reg_compliance_engine/` – Ensures Department of Labor regulation compliance.  
- `gaap_ledger_porter/` – Handles export and import of GAAP-compliant ledgers.  
- `gdpr_ccpa_core/` – Core utilities for GDPR and CCPA privacy compliance.  
- `hbs_model_validator/` – Validates HBS models for consistency and compliance.  
- `lse_impact_simulator/` – Simulates impacts in the London Stock Exchange environment.  
- `multivoice_compliance_ui/` – User interface for multi-language compliance workflows.  
- [`modules/`](modules/README.md) – Core modules for Prep Phase 13.  
- [`phase12/`](phase12/README.md) – Hyper-edge accessibility modules.  
- `prep/` – Shared utilities for the Prep platform.  
- [`prepchef/`](prepchef/README.md) – Downtime-only, compliant commercial-kitchen marketplace.  
- `tests/` – Pytest-based unit tests for the repository.

## Further Documentation
- [TECHNICAL_OUTLINE.md](TECHNICAL_OUTLINE.md)
- Additional details are available in each subproject's README (linked above where available).

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

