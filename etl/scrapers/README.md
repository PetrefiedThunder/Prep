# ETL Scrapers

## Refreshing San Bernardino County health requirements seed

The San Bernardino County loader (`sbcounty_health.py`) reads requirement rows
from the JSON seed at `data/state/ca_san_bernardino_requirements.json`.
Operations can refresh the seeded requirements with the following workflow:

1. Open the JSON file in your preferred editor and update the requirement
   objects. Each object should contain the keys `id`, `name`, `description`,
   `source_url`, `jurisdiction`, `expiration_interval`, and `cert_type`.
2. Ensure the JSON remains a valid array of objects (you can run
   `python -m json.tool data/state/ca_san_bernardino_requirements.json` to
   validate formatting).
3. Load the updates into Postgres:
   ```bash
   python -m etl.scrapers.sbcounty_health
   ```

The loader computes hashes from the requirement content, so any changes to the
seeded rows will be detected and upserted into the `regdocs` table.
