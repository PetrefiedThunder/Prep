import os
import random
import requests
import sys

BASE = os.getenv("API_BASE_URL", "http://localhost:8787")

# Require admin token from environment for security
ADMIN_TOKEN = os.getenv("SEED_ADMIN_TOKEN")
if not ADMIN_TOKEN:
    print("ERROR: SEED_ADMIN_TOKEN environment variable must be set.", file=sys.stderr)
    print("Never use hardcoded authentication tokens.", file=sys.stderr)
    sys.exit(1)

HEADERS = {"Authorization": f"Bearer {ADMIN_TOKEN}"}


def post(path: str, payload: dict) -> dict:
    """POST helper that raises for non-2xx responses."""
    response = requests.post(
        f"{BASE}{path}",
        json=payload,
        headers=HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


HOSTS = [
    {
        "legal_name": "JT Diner LLC",
        "ein": "12-3456789",
        "address": "61719 Twentynine Palms Hwy, Joshua Tree, CA",
        "jurisdiction": "san_bernardino_county",
        "permit_id": "JT-2025-001",
        "price_hour": 45,
        "blackouts": [{"start": "08:00", "end": "11:30"}],
    },
    {
        "legal_name": "Sunset Eats Inc",
        "ein": "98-7654321",
        "address": "123 Market St, San Francisco, CA",
        "jurisdiction": "san_francisco",
        "permit_id": "SF-2025-337",
        "price_hour": 65,
        "blackouts": [{"start": "16:00", "end": "23:00"}],
    },
    {
        "legal_name": "Echo Park Kitchen LP",
        "ein": "11-2233445",
        "address": "1400 Sunset Blvd, Los Angeles, CA",
        "jurisdiction": "los_angeles",
        "permit_id": "LA-2025-992",
        "price_hour": 55,
        "blackouts": [{"start": "17:00", "end": "22:00"}],
    },
]

PRODUCT_TYPES = ["baked_goods", "meal_prep", "vegan_catering", "cold_beverages"]
JURISDICTIONS = [
    "san_francisco",
    "los_angeles",
    "san_bernardino_county",
]


def seed_hosts() -> list[str]:
    host_ids: list[str] = []
    for host_payload in HOSTS:
        response = post("/onboarding/host", host_payload)
        host_ids.append(response["host_id"])
    return host_ids


def seed_makers(count: int = 10) -> list[str]:
    maker_ids: list[str] = []
    for index in range(count):
        maker_payload = {
            "legal_name": f"Maker {index + 1} LLC",
            "entity": "llc",
            "product_types": [random.choice(PRODUCT_TYPES)],
            "home_jurisdiction": random.choice(JURISDICTIONS),
            "has_permits": bool(random.getrandbits(1)),
        }
        response = post("/onboarding/maker", maker_payload)
        maker_ids.append(response["maker_id"])
    return maker_ids


def seed_availability(host_ids: list[str], days: int = 7) -> None:
    for host_id in host_ids:
        for offset in range(1, days + 1):
            payload = {
                "host_id": host_id,
                "date_offset_days": offset,
                "start": "06:00",
                "end": "15:00",
                "buffer_minutes": 30,
            }
            post("/availability", payload)


def main() -> None:
    host_ids = seed_hosts()
    maker_ids = seed_makers(count=10)
    seed_availability(host_ids)
    print({"hosts": host_ids, "makers": maker_ids})


if __name__ == "__main__":
    main()
