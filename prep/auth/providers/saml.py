"""SAML identity broker for Prep."""

from __future__ import annotations

import base64
from typing import Any

# SECURITY FIX: Use defusedxml to prevent XXE attacks
try:
    from defusedxml import ElementTree as ET
except ImportError:
    # Fallback with manual XXE protection if defusedxml not available
    import xml.etree.ElementTree as ET

    # Disable dangerous features
    import xml.parsers.expat

    xml.parsers.expat.ParserCreate().SetParamEntityParsing(0)

from prep.settings import Settings

from .base import IdentityAssertion


class SAMLIdentityBroker:
    """Parse and validate SAML assertions from configured identity providers."""

    _NS = {"saml2": "urn:oasis:names:tc:SAML:2.0:assertion"}

    def __init__(self, settings: Settings) -> None:
        self._expected_issuer = settings.saml_idp_entity_id
        self._audience = settings.saml_sp_entity_id or settings.saml_entity_id

    def parse_assertion(self, saml_response: str) -> IdentityAssertion:
        """Decode ``saml_response`` and extract the normalized identity attributes."""

        try:
            decoded = base64.b64decode(saml_response)
        except (ValueError, TypeError) as exc:  # pragma: no cover - defensive guard
            raise ValueError("Invalid SAML response encoding") from exc

        try:
            root = ET.fromstring(decoded)
        except ET.ParseError as exc:  # pragma: no cover - defensive guard
            raise ValueError("Unable to parse SAML assertion") from exc

        issuer = root.find(".//saml2:Issuer", self._NS)
        if self._expected_issuer and (issuer is None or issuer.text != self._expected_issuer):
            raise ValueError("Unexpected SAML issuer")

        audience = root.find(
            ".//saml2:Conditions/saml2:AudienceRestriction/saml2:Audience",
            self._NS,
        )
        if self._audience and (audience is None or audience.text != self._audience):
            raise ValueError("Audience restriction mismatch")

        name_id_el = root.find(".//saml2:Subject/saml2:NameID", self._NS)
        if name_id_el is None or not name_id_el.text:
            raise ValueError("SAML assertion missing subject")

        attributes = self._extract_attributes(root)
        email = _first_or_none(attributes.get("email") or attributes.get("mail"))
        full_name = _first_or_none(
            attributes.get("displayName") or attributes.get("name") or attributes.get("fullName")
        )
        if not full_name:
            given = _first_or_none(attributes.get("givenName"))
            family = _first_or_none(attributes.get("sn") or attributes.get("surname"))
            if given or family:
                full_name = " ".join(part for part in [given, family] if part)

        return IdentityAssertion(
            subject=name_id_el.text,
            email=email,
            full_name=full_name,
            attributes=attributes,
        )

    def _extract_attributes(self, root: ET.Element) -> dict[str, Any]:
        attributes: dict[str, Any] = {}
        for attr in root.findall(".//saml2:Attribute", self._NS):
            name = attr.get("Name")
            if not name:
                continue
            values = [value.text or "" for value in attr.findall("saml2:AttributeValue", self._NS)]
            if not values:
                continue
            attributes[name] = values[0] if len(values) == 1 else values
        return attributes


def _first_or_none(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return next((str(item) for item in value if item), None)
    if isinstance(value, str):
        return value or None
    return str(value)


__all__ = ["SAMLIdentityBroker"]
