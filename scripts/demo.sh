#!/usr/bin/env bash
set -euo pipefail
API="${API_BASE_URL:?set API_BASE_URL}"; AUTH="Bearer ${SEED_ADMIN_TOKEN:?set SEED_ADMIN_TOKEN}"

echo "1) Make sure health is green"
curl -fsS "$API/healthz" >/dev/null && echo "✅ Health OK"

echo "2) Get sample maker & kitchen"
MK=$(curl -s "$API/debug/random_maker" | jq -r .maker_id)
KT=$(curl -s "$API/debug/random_kitchen" | jq -r .kitchen_id)
echo "Maker: $MK  Kitchen: $KT"

echo "3) Compliance evaluate"
curl -s -X POST "$API/compliance/evaluate" -H "Authorization: $AUTH" -H "Content-Type: application/json" \
  -d "{\"maker_id\":\"$MK\",\"kitchen_id\":\"$KT\",\"date\":\"2025-11-05T10:00:00-08:00\"}" | jq

echo "4) Create booking"
B=$(curl -s -X POST "$API/bookings" -H "Authorization: $AUTH" -H "Content-Type: application/json" \
  -d "{\"maker_id\":\"$MK\",\"kitchen_id\":\"$KT\",\"start\":\"2025-11-05T10:00:00-08:00\",\"end\":\"2025-11-05T12:00:00-08:00\",\"deposit_cents\":10000,\"quote\":{\"hourly_cents\":6500,\"hours\":2,\"cleaning_cents\":1500,\"platform_fee_bps\":1000}}")
echo "$B" | jq
BK=$(echo "$B" | jq -r .booking_id)

echo "5) Confirm booking"
curl -s -X POST "$API/bookings/$BK/confirm" -H "Authorization: $AUTH" | jq
echo "✅ Demo complete"
