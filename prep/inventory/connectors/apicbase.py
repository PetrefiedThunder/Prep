"""Connector that fetches menu insights from Apicbase."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Mapping, MutableMapping
from datetime import UTC, datetime
from typing import Any

try:  # pragma: no cover - optional dependency
    import requests
except Exception:  # pragma: no cover - fall back for environments without requests
    requests = None  # type: ignore

from prep.inventory.errors import ConnectorError

LOGGER = logging.getLogger("inventory.apicbase")
if not LOGGER.handlers:
    LOGGER.addHandler(logging.NullHandler())


class ApicbaseConnector:
    """Thin REST wrapper for Apicbase's recipe endpoints."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        location_id: str | None = None,
        timeout: int = 20,
        session: requests.Session | None = None,
    ) -> None:
        if not requests:
            raise RuntimeError("requests is required to use ApicbaseConnector")

        self.base_url = base_url.rstrip("/") + "/"
        self.api_key = api_key
        self.location_id = location_id
        self.timeout = timeout
        self._session = session or requests.Session()

    def _request(
        self, method: str, path: str, *, params: Mapping[str, Any] | None = None
    ) -> Mapping[str, Any]:
        url = f"{self.base_url}{path.lstrip('/')}"
        headers = {"X-API-Key": self.api_key}
        response = self._session.request(
            method,
            url,
            params=params,
            headers=headers,
            timeout=self.timeout,
        )
        if response.status_code >= 400:
            raise ConnectorError(
                "Apicbase", f"{method} {path} failed", status_code=response.status_code
            )
        try:
            payload = response.json()
        except ValueError as exc:  # pragma: no cover - defensive guard
            raise ConnectorError("Apicbase", "Invalid JSON response") from exc
        if isinstance(payload, Mapping):
            return payload
        raise ConnectorError("Apicbase", "Unexpected response payload shape")

    def _get(self, path: str, *, params: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        return self._request("GET", path, params=params)

    def fetch_recipes(self) -> list[Mapping[str, Any]]:
        """Return recipe metadata including allergens."""

        params: dict[str, Any] = {}
        if self.location_id:
            params["location"] = self.location_id
        payload = self._get("recipes", params=params)
        recipes = payload.get("recipes") if isinstance(payload, Mapping) else None
        if isinstance(recipes, list):
            return recipes  # type: ignore[return-value]
        if isinstance(payload, list):
            return payload  # type: ignore[return-value]
        return []

    def fetch_recipe_costs(self) -> Mapping[str, Any]:
        """Return the most recent recipe costing data."""

        params: dict[str, Any] = {}
        if self.location_id:
            params["location"] = self.location_id
        payload = self._get("recipes/costs", params=params)
        if isinstance(payload, Mapping):
            return payload
        return {}

    def fetch_allergens(self) -> list[Mapping[str, Any]]:
        """Return allergen flags per recipe."""

        params: dict[str, Any] = {}
        if self.location_id:
            params["location"] = self.location_id
        payload = self._get("recipes/allergens", params=params)
        allergens = payload.get("allergens") if isinstance(payload, Mapping) else None
        if isinstance(allergens, list):
            return allergens  # type: ignore[return-value]
        if isinstance(payload, list):
            return payload  # type: ignore[return-value]
        return []

    def build_compliance_snapshot(self) -> dict[str, Any]:
        """Produce an enriched structure suitable for the compliance engine."""

        recipes = self.fetch_recipes()
        cost_payload = self.fetch_recipe_costs()
        allergen_records = self.fetch_allergens()

        cost_lookup: MutableMapping[str, Mapping[str, Any]] = {}
        if isinstance(cost_payload, Mapping):
            raw_costs = cost_payload.get("costs") or cost_payload.get("recipes")
            if isinstance(raw_costs, list):
                for entry in raw_costs:
                    if isinstance(entry, Mapping) and entry.get("recipe_id"):
                        cost_lookup[str(entry["recipe_id"])] = entry
            elif isinstance(raw_costs, Mapping):
                cost_lookup.update(
                    {
                        str(key): value
                        for key, value in raw_costs.items()
                        if isinstance(value, Mapping)
                    }
                )

        allergen_lookup: MutableMapping[str, list[Mapping[str, Any]]] = defaultdict(list)
        for entry in allergen_records:
            if not isinstance(entry, Mapping):
                continue
            recipe_id = entry.get("recipe_id") or entry.get("id")
            if not recipe_id:
                continue
            allergen_lookup[str(recipe_id)].append(entry)

        enriched_recipes: list[dict[str, Any]] = []
        allergen_summary: MutableMapping[str, dict[str, Any]] = defaultdict(
            lambda: {"recipes": 0, "undeclared": 0}
        )
        now = datetime.now(UTC).isoformat()
        for recipe in recipes:
            if not isinstance(recipe, Mapping):
                continue
            recipe_id = str(recipe.get("id") or recipe.get("recipe_id") or "")
            if not recipe_id:
                continue
            enriched: dict[str, Any] = {
                "id": recipe_id,
                "name": recipe.get("name") or recipe.get("title"),
                "category": recipe.get("category"),
                "updated_at": recipe.get("updated_at") or now,
            }
            cost = cost_lookup.get(recipe_id)
            if cost:
                enriched["portion_cost"] = cost.get("portion_cost") or cost.get("cost")
                enriched["gross_margin"] = cost.get("gross_margin")
            allergens = []
            for raw_allergen in allergen_lookup.get(recipe_id, []):
                allergen_name = raw_allergen.get("name") or raw_allergen.get("allergen")
                if not allergen_name:
                    continue
                present = bool(raw_allergen.get("present", True))
                declared = bool(raw_allergen.get("declared", present))
                allergens.append(
                    {
                        "name": allergen_name,
                        "present": present,
                        "declared": declared,
                        "severity": raw_allergen.get("severity") or "medium",
                    }
                )
                summary = allergen_summary[allergen_name]
                summary["recipes"] += 1
                if present and not declared:
                    summary["undeclared"] += 1
            enriched["allergens"] = allergens
            enriched_recipes.append(enriched)

        return {
            "recipes": enriched_recipes,
            "allergens_summary": dict(allergen_summary),
            "fetched_at": now,
        }

    def enrich_payload(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Return a copy of ``payload`` enriched with Apicbase insights."""

        snapshot = self.build_compliance_snapshot()
        enriched = dict(payload)
        enriched.setdefault("recipes", snapshot["recipes"])
        enriched.setdefault("allergens_summary", snapshot["allergens_summary"])
        return enriched


__all__ = ["ApicbaseConnector"]
