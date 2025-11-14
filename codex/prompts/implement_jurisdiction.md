System:
You are an expert engineer adding a new jurisdiction to the Prep compliance engine.

User:
Implement a jurisdiction under `apps/city_regulatory_service/jurisdictions/<name>/` with:
- `ingest.py` → `fetch_regulations()` returning harmonized metadata
- `validate.py` → queries OPA at `${OPA_URL}/v1/data/<package>/allow`, logs decision via `apps/compliance/log_writer.py`, returns dict {allow, decision_id, rationale}
- `policy.rego` → exposes `allow` with non-expired permit and minimum inspection score

Constraints:
- No secrets, no network calls in tests
- Add tests under `tests/policy/<region>` to assert allow/deny
- Keep interfaces consistent with San Francisco/Oakland/Joshua Tree
