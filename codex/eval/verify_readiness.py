from __future__ import annotations
import os, sys, json
import psycopg2
import requests

OPA = os.environ.get("OPA_URL", "http://localhost:8181")
DB  = os.environ.get("DATABASE_URL", "postgresql://prep:prep@localhost:5432/prep")

def _assert_sf_allows():
    payload = {"input":{
        "permit":{"type":"food_prep","expiry":"2099-01-01"},
        "facility":{"inspection_score":95}
    }}
    r = requests.post(f"{OPA}/v1/data/city/san_francisco/food_permit/allow", json=payload, timeout=3)
    r.raise_for_status()
    assert r.json().get("result") is True, "SF policy should allow valid input"

def _db_has_rows(jurisdictions):
    conn = psycopg2.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM policy_decisions WHERE jurisdiction = ANY(%s)", (jurisdictions,))
    n = cur.fetchone()[0]
    conn.close()
    assert n > 0, f"Expected policy_decisions rows for {jurisdictions}, found {n}"

def main():
    # OPA sanity
    requests.get(f"{OPA}/health", timeout=2)
    _assert_sf_allows()
    # DB logging sanity (jurisdictions likely exercised by tests)
    _db_has_rows(["san_francisco","oakland","joshua_tree"])
    print(json.dumps({"status":"ok"}))
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(json.dumps({"status":"fail","error":str(e)}))
        sys.exit(1)
