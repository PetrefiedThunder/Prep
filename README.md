# Prep

This repository holds the skeleton for various compliance and financial modules.

## Environment Setup

1. Ensure you have **Python 3.9+** installed.
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install requirements (none yet, placeholder):
   ```bash
   pip install -r requirements.txt
   ```

## Module Overview

The `src/` directory contains placeholders for planned modules:

- `hbs_model_validator` - Tools for validating HBS models.
- `dol_reg_compliance_engine` - Engine for DoL regulation compliance checks.
- `gaap_ledger_porter` - GAAP ledger export/import utilities.
- `gdpr_ccpa_core` - Shared GDPR/CCPA compliance logic.
- `lse_impact_simulator` - Simulator assessing LSE impacts.
- `auto_projection_bot` - Automated projection generation bot.
- `multi_voice_compliance_ui` - Web UI for multi-voice compliance tasks.

Each submodule currently contains an empty `__init__.py` file and will be further developed.
