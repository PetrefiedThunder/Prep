# Regulatory Horizon Engine (RHE)

Initial scaffolding for Prep's predictive regulation service. The service is
split into modular components that will eventually coordinate automated source
 discovery, multi-modal parsing, predictive modeling, and JSONPatch codification.

## Components

- `finders/` – LLM-assisted discovery agents that identify municipal and state
  data sources.
- `parsers/` – Document retrieval and extraction pipelines with OCR and
  classification hooks.
- `predictors/` – Momentum and relevance models that forecast passage
  probabilities.
- `codifiers/` – Utilities that transform proposal text into machine-readable
  future-state diffs.
- `api/` – FastAPI application exposing ingestion and prediction endpoints.
- `dags/` – Schedule stubs for orchestration tools like Airflow or Dagster.

The current implementation focuses on type-safe scaffolding so downstream Codex
iterations can attach real crawlers, parsers, and models without restructuring
boilerplate.
