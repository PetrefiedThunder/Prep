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

## Testing
Run the test suite with:
```bash
pytest
```

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

