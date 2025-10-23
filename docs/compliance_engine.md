# Compliance Engine Overview

The compliance engine provides a unified framework for validating Prep data and
workflows against a wide spectrum of regulatory requirements. Each compliance
area is encapsulated in a dedicated engine that derives from a shared
`ComplianceEngine` base class, ensuring consistent rule definitions, violation
reporting, and score calculation.

## Core Components

- **Base Engine (`prep/compliance/base_engine.py`)** – Supplies the shared data
  structures and `generate_report` workflow used by every engine.
- **DOL Engine (`prep/compliance/dol_reg_compliance_engine.py`)** – Evaluates wage
  and hour practices, record keeping, and break policies for U.S. Department of
  Labor compliance.
- **GDPR/CCPA Engine (`prep/compliance/gdpr_ccpa_core.py`)** – Checks consent
  management, data minimisation, deletion workflows, breach notification, and
  third-party data sharing controls.
- **HBS Model Validator (`prep/compliance/hbs_model_validator.py`)** – Validates
  business model artefacts against Harvard Business School guidance with
  structure, documentation, and validation requirements.
- **LSE Impact Simulator (`prep/compliance/lse_impact_simulator.py`)** – Monitors
  market conduct obligations and simulates market impact scenarios for London
  Stock Exchange compliance.
- **MultiVoice UI Engine (`prep/compliance/multivoice_compliance_ui.py`)** –
  Ensures accessibility, localisation, consent, and transparency expectations
  across multilingual interfaces.
- **Coordinator (`prep/compliance/coordinator.py`)** – Orchestrates all engines
  to deliver comprehensive audits, executive summaries, and prioritised
  recommendations.

## Command Line Interface

Run an end-to-end audit by invoking the CLI:

```bash
prep-compliance --audit --data path/to/data.json --output reports/latest.json
```

The command produces a structured JSON report, prints an executive summary, and
highlights the top recommendations.

## Timestamp Semantics

All compliance engines must generate timezone-aware UTC datetimes when
recording rule metadata, report timestamps, or violations. Use
`datetime.now(timezone.utc)` (or an equivalent helper) so that downstream
systems can safely compare and serialize timestamps without ambiguity.

## Configuration

Engine behaviour is configurable through `config/compliance.yaml`. When the file
is absent a sensible default configuration is loaded and can be customised via
`ComplianceConfigManager`.

- **enabled_engines** – Controls which audit engines the CLI will run. Provide a
  list of engine keys (e.g. `dol`, `privacy`, `hbs`, `lse`, `ui`). Any engines
  omitted from this list are skipped when `prep-compliance --audit` executes,
  allowing you to disable domains that are not relevant to a deployment. If the
  setting is omitted, all available engines are executed by default.

## Testing

Execute the compliance test suite with:

```bash
pytest tests/compliance
```

These tests cover the base engine, selected domain engines, and the coordinator
workflow.
