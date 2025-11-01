import os, time, hmac, hashlib, json, requests
secret = os.environ.get("PREP_WEBHOOK_SECRET", "devsecret")
url = os.environ.get("PREP_WEBHOOK_URL", "http://localhost:8787/webhooks/prep")
payload = {
  "type": "fees.updated",
  "id": "11111111-1111-1111-1111-111111111111",
  "created_at": "2025-10-31T19:02:00Z",
  "data": {
    "jurisdiction": "san_francisco",
    "etag": "abcd",
    "version": "2025-10",
    "totals": {"one_time_cents": 45000, "recurring_annualized_cents": 98000, "incremental_fee_count": 1}
  }
}
raw = json.dumps(payload, separators=(",", ":")).encode()
ts = int(time.time())
sig = hmac.new(secret.encode(), f"{ts}.".encode() + raw, hashlib.sha256).hexdigest()
headers = {
  "Prep-Event": payload["type"],
  "Prep-Event-Id": payload["id"],
  "Prep-Signature": f"t={ts},v1={sig}",
  "Content-Type": "application/json",
}
r = requests.post(url, data=raw, headers=headers, timeout=10)
print(r.status_code, r.text)
