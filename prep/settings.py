"""Environment-aware configuration for the Prep platform."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable
from typing import Any, Dict, List

from pydantic import (
    AnyUrl,
    BaseModel,
    Field,
    PostgresDsn,
    ValidationError,
    ValidationInfo,
    field_validator,
)

_ENV_FILE_ENV = "PREP_ENV_FILE"
_DEFAULT_ENV_FILE = Path(".env")


def _parse_env_file(path: Path) -> Dict[str, str]:
    """Parse a simple ``.env`` file into a dictionary."""

    values: Dict[str, str] = {}
    if not path.exists() or not path.is_file():
        return values

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


class IntegrationEndpoint(BaseModel):
    """Configuration for an external integration health check."""

    id: str = Field(alias="id")
    name: str = Field(alias="name")
    url: AnyUrl = Field(alias="url")
    description: str | None = Field(default=None, alias="description")

    model_config = {
        "populate_by_name": True,
        "extra": "ignore",
    }


class RBACPolicy(BaseModel):
    """Declarative RBAC rule describing required roles for a path prefix."""

    path_prefix: str = Field(alias="path_prefix", min_length=1)
    roles: list[str] = Field(default_factory=list, alias="roles")

    model_config = {
        "populate_by_name": True,
        "extra": "ignore",
    }


class Settings(BaseModel):
    """Strongly typed runtime configuration."""

    environment: str = Field(default="development", alias="ENVIRONMENT")
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://prep:prep@localhost:5432/prep", alias="DATABASE_URL"
    )
    redis_url: AnyUrl = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    database_pool_size: int = Field(default=10, ge=1, alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, ge=0, alias="DATABASE_MAX_OVERFLOW")
    database_pool_timeout: int = Field(default=30, ge=1, alias="DATABASE_POOL_TIMEOUT")
    database_pool_recycle: int = Field(default=1800, ge=1, alias="DATABASE_POOL_RECYCLE")
    session_ttl_seconds: int = Field(default=3600, ge=300, alias="SESSION_TTL_SECONDS")
    session_max_age_minutes: int = Field(
        default=480, ge=30, alias="SESSION_MAX_AGE_MINUTES"
    )
    secret_key: str = Field(default="change-me", alias="SECRET_KEY")
    auth_signing_key: str | None = Field(default=None, alias="AUTH_SIGNING_KEY")
    access_token_expire_minutes: int = Field(default=60, ge=5, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_ttl_days: int = Field(
        default=30, ge=1, alias="REFRESH_TOKEN_TTL_DAYS"
    )
    auth_oidc_metadata: Dict[str, Any] = Field(
        default_factory=dict, alias="AUTH_OIDC_METADATA"
    )
    auth_saml_metadata: Dict[str, Any] = Field(
        default_factory=dict, alias="AUTH_SAML_METADATA"
    )
    auth_signing_public_key: str | None = Field(
        default=None, alias="AUTH_SIGNING_PUBLIC_KEY"
    )
    auth_signing_private_key: str | None = Field(
        default=None, alias="AUTH_SIGNING_PRIVATE_KEY"
    )
    auth_ip_allowlist: List[str] = Field(
        default_factory=list, alias="AUTH_IP_ALLOWLIST"
    )
    auth_device_allowlist: List[str] = Field(
        default_factory=list, alias="AUTH_DEVICE_ALLOWLIST"
    )
    refresh_token_ttl_seconds: int = Field(
        default=60 * 60 * 24 * 14,
        ge=3600,
        alias="REFRESH_TOKEN_TTL_SECONDS",
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    oidc_issuer: str | None = Field(default=None, alias="OIDC_ISSUER")
    oidc_audience: str | None = Field(default=None, alias="OIDC_AUDIENCE")
    oidc_client_id: str | None = Field(default=None, alias="OIDC_CLIENT_ID")
    oidc_client_secret: str | None = Field(default=None, alias="OIDC_CLIENT_SECRET")
    oidc_jwks_url: AnyUrl | None = Field(default=None, alias="OIDC_JWKS_URL")
    saml_sp_entity_id: str | None = Field(default=None, alias="SAML_SP_ENTITY_ID")
    saml_entity_id: str | None = Field(default=None, alias="SAML_ENTITY_ID")
    saml_idp_metadata_url: AnyUrl | None = Field(default=None, alias="SAML_IDP_METADATA_URL")
    saml_idp_entity_id: str | None = Field(default=None, alias="SAML_IDP_ENTITY_ID")
    stripe_secret_key: str | None = Field(default=None, alias="STRIPE_SECRET_KEY")
    stripe_connect_refresh_url: AnyUrl = Field(
        default="https://example.com/stripe/refresh", alias="STRIPE_CONNECT_REFRESH_URL"
    )
    stripe_connect_return_url: AnyUrl = Field(
        default="https://example.com/stripe/return", alias="STRIPE_CONNECT_RETURN_URL"
    )
    stripe_api_key: str | None = Field(default=None, alias="STRIPE_API_KEY")
    stripe_currency: str = Field(default="usd", alias="STRIPE_CURRENCY")
    use_fixtures: bool = Field(default=False, alias="USE_FIXTURES")
    compliance_controls_enabled: bool = Field(
        default=False, alias="COMPLIANCE_CONTROLS_ENABLED"
    )
    twilio_from_number: str | None = Field(default=None, alias="TWILIO_FROM_NUMBER")
    compliance_ops_phone: str | None = Field(default=None, alias="COMPLIANCE_OPS_PHONE")
    compliance_ops_email: str | None = Field(default=None, alias="COMPLIANCE_OPS_EMAIL")
    alert_email_sender: str = Field(default="alerts@prep.test", alias="ALERT_EMAIL_SENDER")
    doordash_drive_client_id: str | None = Field(
        default=None, alias="DOORDASH_DRIVE_CLIENT_ID"
    )
    doordash_drive_client_secret: str | None = Field(
        default=None, alias="DOORDASH_DRIVE_CLIENT_SECRET"
    )
    doordash_drive_base_url: AnyUrl = Field(
        default="https://api.doordash.com", alias="DOORDASH_DRIVE_BASE_URL"
    )
    doordash_drive_webhook_secret: str | None = Field(
        default=None, alias="DOORDASH_DRIVE_WEBHOOK_SECRET"
    )
    uber_direct_client_id: str | None = Field(
        default=None, alias="UBER_DIRECT_CLIENT_ID"
    )
    uber_direct_client_secret: str | None = Field(
        default=None, alias="UBER_DIRECT_CLIENT_SECRET"
    )
    uber_direct_scope: str = Field(default="delivery", alias="UBER_DIRECT_SCOPE")
    uber_direct_audience: str = Field(
        default="https://api.uber.com", alias="UBER_DIRECT_AUDIENCE"
    )
    uber_direct_base_url: AnyUrl = Field(
        default="https://api.uber.com", alias="UBER_DIRECT_BASE_URL"
    )
    uber_direct_token_url: AnyUrl = Field(
        default="https://login.uber.com/oauth/v2/token", alias="UBER_DIRECT_TOKEN_URL"
    )
    docusign_base_url: AnyUrl = Field(
        default="https://demo.docusign.net/restapi", alias="DOCUSIGN_BASE_URL"
    )
    docusign_account_id: str | None = Field(default=None, alias="DOCUSIGN_ACCOUNT_ID")
    docusign_access_token: str | None = Field(default=None, alias="DOCUSIGN_ACCESS_TOKEN")
    docusign_sublease_template_id: str | None = Field(
        default=None, alias="DOCUSIGN_SUBLEASE_TEMPLATE_ID"
    )
    docusign_return_url: AnyUrl = Field(
        default="https://example.com/docusign/return", alias="DOCUSIGN_RETURN_URL"
    )
    docusign_ping_url: AnyUrl | None = Field(default=None, alias="DOCUSIGN_PING_URL")
    contracts_s3_bucket: str | None = Field(default=None, alias="CONTRACTS_S3_BUCKET")
    stripe_webhook_secret: str | None = Field(
        default=None, alias="STRIPE_WEBHOOK_SECRET"
    )
    onfleet_api_key: str | None = Field(default=None, alias="ONFLEET_API_KEY")
    onfleet_base_url: AnyUrl = Field(
        default="https://onfleet.com/api/v2", alias="ONFLEET_BASE_URL"
    )
    shopify_store_domain: str | None = Field(default=None, alias="SHOPIFY_STORE_DOMAIN")
    shopify_admin_api_token: str | None = Field(
        default=None, alias="SHOPIFY_ADMIN_API_TOKEN"
    )
    shopify_api_version: str = Field(default="2024-01", alias="SHOPIFY_API_VERSION")
    tiktok_shop_app_key: str | None = Field(default=None, alias="TIKTOK_SHOP_APP_KEY")
    tiktok_shop_app_secret: str | None = Field(
        default=None, alias="TIKTOK_SHOP_APP_SECRET"
    )
    tiktok_shop_access_token: str | None = Field(
        default=None, alias="TIKTOK_SHOP_ACCESS_TOKEN"
    )
    oracle_simphony_host: AnyUrl | None = Field(
        default=None, alias="ORACLE_SIMPHONY_HOST"
    )
    oracle_simphony_username: str | None = Field(
        default=None, alias="ORACLE_SIMPHONY_USERNAME"
    )
    oracle_simphony_password: str | None = Field(
        default=None, alias="ORACLE_SIMPHONY_PASSWORD"
    )
    oracle_simphony_enterprise_id: str | None = Field(
        default=None, alias="ORACLE_SIMPHONY_ENTERPRISE_ID"
    )
    bigquery_project_id: str | None = Field(
        default=None, alias="BIGQUERY_PROJECT_ID"
    )
    bigquery_dataset: str | None = Field(default=None, alias="BIGQUERY_DATASET")
    snowflake_account: str | None = Field(default=None, alias="SNOWFLAKE_ACCOUNT")
    snowflake_database: str | None = Field(default=None, alias="SNOWFLAKE_DATABASE")
    snowflake_schema: str | None = Field(default=None, alias="SNOWFLAKE_SCHEMA")
    snowflake_warehouse: str | None = Field(
        default=None, alias="SNOWFLAKE_WAREHOUSE"
    )
    schema_registry_url: AnyUrl | None = Field(
        default=None, alias="SCHEMA_REGISTRY_URL"
    )
    kafka_bootstrap_servers: str | None = Field(
        default=None, alias="KAFKA_BOOTSTRAP_SERVERS"
    )
    integration_endpoints: list[IntegrationEndpoint] = Field(
        default_factory=list, alias="INTEGRATION_ENDPOINTS"
    )
    integrations_beta_enabled: bool = Field(
        default=False, alias="INTEGRATIONS_BETA"
    )
    integration_health_timeout_seconds: int = Field(
        default=10, ge=1, alias="INTEGRATION_HEALTH_TIMEOUT_SECONDS"
    )
    ip_allowlist: list[str] = Field(default_factory=list, alias="IP_ALLOWLIST")
    device_allowlist: list[str] = Field(default_factory=list, alias="DEVICE_ALLOWLIST")
    session_optional_paths: list[str] = Field(
        default_factory=lambda: [
            "/api/v1/auth/token",
            "/api/v1/platform/auth/login",
            "/api/v1/platform/users/register",
            "/healthz",
        ],
        alias="SESSION_OPTIONAL_PATHS",
    )
    rbac_policies: list[RBACPolicy] = Field(
        default_factory=lambda: [
            RBACPolicy(path_prefix="/api/v1/platform/admin", roles=["operator_admin", "support_analyst"]),
            RBACPolicy(
                path_prefix="/api/v1/platform/kitchens",
                roles=["operator_admin", "kitchen_manager"],
            ),
            RBACPolicy(
                path_prefix="/api/v1/platform/reviews",
                roles=["food_business_admin", "city_reviewer", "support_analyst"],
            ),
        ],
        alias="RBAC_POLICIES",
    )
    rbac_excluded_paths: list[str] = Field(
        default_factory=lambda: ["/healthz"], alias="RBAC_EXCLUDED_PATHS"
    )
    square_client_id: str | None = Field(default=None, alias="SQUARE_CLIENT_ID")
    square_client_secret: str | None = Field(default=None, alias="SQUARE_CLIENT_SECRET")
    square_base_url: AnyUrl = Field(
        default="https://connect.squareup.com", alias="SQUARE_BASE_URL"
    )
    toast_api_key: str | None = Field(default=None, alias="TOAST_API_KEY")
    toast_base_url: AnyUrl = Field(default="https://toast-api.io", alias="TOAST_BASE_URL")
    pos_ledger_bucket: str | None = Field(default=None, alias="POS_LEDGER_BUCKET")
    next_insurance_api_key: str | None = Field(default=None, alias="NEXT_INSURANCE_API_KEY")
    thimble_api_key: str | None = Field(default=None, alias="THIMBLE_API_KEY")
    pilot_zip_codes: list[str] = Field(default_factory=list, alias="PILOT_ZIP_CODES")
    pilot_counties: list[str] = Field(default_factory=list, alias="PILOT_COUNTIES")

    model_config = {
        "populate_by_name": True,
        "extra": "ignore",
    }

    @field_validator("environment")
    @classmethod
    def _validate_environment(cls, value: str) -> str:
        allowed = {"development", "staging", "production"}
        normalized = value.lower()
        if normalized not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {sorted(allowed)}")
        return normalized

    @field_validator("stripe_secret_key", "stripe_api_key", "stripe_webhook_secret")
    @classmethod
    def _validate_stripe_keys(cls, value: str | None, info: ValidationInfo) -> str | None:
        if value is not None and value.strip() == "":
            raise ValueError(f"{info.field_name} cannot be an empty string")
        return value

    @field_validator(
        "ip_allowlist",
        "device_allowlist",
        "session_optional_paths",
        "rbac_excluded_paths",
        mode="before",
    )
    @classmethod
    def _parse_csv_list(cls, value: Any) -> list[str]:
        if value in (None, ""):
            return []
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                return [item.strip() for item in stripped.split(",") if item.strip()]
            if isinstance(parsed, Iterable):
                return [str(item).strip() for item in parsed if str(item).strip()]
            raise TypeError("Expected list-compatible value for allowlist configuration")
        if isinstance(value, Iterable):
            return [str(item).strip() for item in value if str(item).strip()]
        raise TypeError("Allowlist configuration must be a list or comma-delimited string")

    @field_validator("rbac_policies", mode="before")
    @classmethod
    def _parse_rbac_policies(cls, value: Any) -> list[dict[str, Any]]:
        if value in (None, ""):
            return []
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValueError("RBAC_POLICIES must be valid JSON") from exc
            if isinstance(parsed, list):
                return parsed
            raise ValueError("RBAC_POLICIES must decode to a list of policies")
        return value

    @field_validator("auth_ip_allowlist", "auth_device_allowlist", mode="before")
    @classmethod
    def _parse_allowlists(cls, value: Any) -> list[str]:
        if value in (None, "", []):
            return []
        if isinstance(value, str):
            normalized = value.replace(";", ",")
            return [item.strip() for item in normalized.split(",") if item.strip()]
        if isinstance(value, Iterable):
            return [str(item).strip() for item in value if str(item).strip()]
        raise TypeError("Allowlist configuration must be a string or iterable")

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_staging(self) -> bool:
        return self.environment == "staging"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @field_validator("pilot_zip_codes", "pilot_counties", mode="before")
    @classmethod
    def _normalize_pilot_collections(
        cls, value: Any, info: ValidationInfo
    ) -> List[str]:
        if value is None or value == "":
            return []
        if isinstance(value, str):
            normalized_source: List[str] = [
                item.strip() for item in value.replace(";", ",").split(",")
            ]
        elif isinstance(value, (list, tuple, set)):
            normalized_source = [str(item).strip() for item in value]
        else:  # pragma: no cover - defensive branch
            raise TypeError(
                f"Unsupported type for {info.field_name}: {type(value)!r}"
            )

        cleaned: List[str] = []
        for item in normalized_source:
            if not item:
                continue
            if info.field_name == "pilot_zip_codes":
                normalized = item.replace(" ", "").upper()
            else:
                normalized = item.upper()
            if normalized not in cleaned:
                cleaned.append(normalized)
        return cleaned


def _collect_environment(env_file: Path | None) -> Dict[str, Any]:
    env: Dict[str, Any] = {}
    if env_file is None:
        env_file = _DEFAULT_ENV_FILE
    env.update(_parse_env_file(env_file))
    env.update(os.environ)
    return env


def load_settings(*, env_file: Path | None = None) -> Settings:
    """Load and validate configuration from environment variables."""

    raw_env = _collect_environment(env_file)
    try:
        return Settings.model_validate(raw_env)
    except ValidationError as exc:  # pragma: no cover - configuration errors
        message = ", ".join(err["msg"] for err in exc.errors())
        raise RuntimeError(f"Invalid configuration: {message}") from exc


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance."""

    env_path = os.getenv(_ENV_FILE_ENV)
    path = Path(env_path) if env_path else _DEFAULT_ENV_FILE
    return load_settings(env_file=path)


__all__ = ["Settings", "IntegrationEndpoint", "get_settings", "load_settings"]
