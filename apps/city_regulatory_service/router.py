"""Canonical jurisdiction router for the city regulatory service."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class JurisdictionRoute:
    """Normalized routing information for a jurisdiction."""

    slug: str
    city: str
    state: str
    opa_package: str

    @property
    def opa_policy_path(self) -> str:
        """Return the dotted package path for the jurisdiction policy."""

        return self.opa_package


_JURISDICTIONS: Mapping[str, JurisdictionRoute] = {
    "oakland": JurisdictionRoute(
        slug="oakland",
        city="Oakland",
        state="CA",
        opa_package="city_regulatory_service.jurisdictions.oakland",
    ),
    "san_francisco": JurisdictionRoute(
        slug="san_francisco",
        city="San Francisco",
        state="CA",
        opa_package="city_regulatory_service.jurisdictions.san_francisco",
    ),
    "berkeley": JurisdictionRoute(
        slug="berkeley",
        city="Berkeley",
        state="CA",
        opa_package="city_regulatory_service.jurisdictions.berkeley",
    ),
    "san_jose": JurisdictionRoute(
        slug="san_jose",
        city="San Jose",
        state="CA",
        opa_package="city_regulatory_service.jurisdictions.san_jose",
    ),
    "palo_alto": JurisdictionRoute(
        slug="palo_alto",
        city="Palo Alto",
        state="CA",
        opa_package="city_regulatory_service.jurisdictions.palo_alto",
    ),
    "joshua_tree": JurisdictionRoute(
        slug="joshua_tree",
        city="Joshua Tree",
        state="CA",
        opa_package="city_regulatory_service.jurisdictions.joshua_tree",
    ),
}

_ALIASES: Mapping[str, str] = {
    "oakland": "oakland",
    "oakland, ca": "oakland",
    "city of oakland": "oakland",
    "oakland california": "oakland",
    "san francisco": "san_francisco",
    "sf": "san_francisco",
    "san francisco, ca": "san_francisco",
    "city of san francisco": "san_francisco",
    "berkeley": "berkeley",
    "berkeley, ca": "berkeley",
    "city of berkeley": "berkeley",
    "berkeley california": "berkeley",
    "san jose": "san_jose",
    "san jose, ca": "san_jose",
    "city of san jose": "san_jose",
    "sj": "san_jose",
    "silicon valley": "san_jose",
    "palo alto": "palo_alto",
    "palo alto, ca": "palo_alto",
    "city of palo alto": "palo_alto",
    "stanford": "palo_alto",
    "stanford area": "palo_alto",
    "joshua tree": "joshua_tree",
    "joshua tree, ca": "joshua_tree",
    "san bernardino county - joshua tree": "joshua_tree",
    "jt": "joshua_tree",
    "joshua tree national park": "joshua_tree",
}


def aliases() -> Mapping[str, str]:
    """Return the mapping of known aliases to jurisdiction slugs."""

    return _ALIASES


def jurisdictions() -> Iterable[JurisdictionRoute]:
    """Yield all known jurisdiction routes."""

    return _JURISDICTIONS.values()


def canonicalize(value: str) -> JurisdictionRoute | None:
    """Resolve a user-supplied jurisdiction string to a canonical route."""

    key = " ".join(value.lower().replace("_", " ").split())
    slug = _ALIASES.get(key)
    if slug is None:
        return None
    return _JURISDICTIONS.get(slug)


__all__ = ["JurisdictionRoute", "aliases", "jurisdictions", "canonicalize"]
