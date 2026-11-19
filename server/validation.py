"""Input validation and normalization for Public IP Inventory records."""

from __future__ import annotations

import ipaddress
from typing import Any

from .config import ENVIRONMENTS, IP_STATUSES, OWNER_TYPES

_ENV_LOOKUP = {env.lower(): env for env in ENVIRONMENTS}
_OWNER_LOOKUP = {owner.lower(): owner for owner in OWNER_TYPES}
_STATUS_LOOKUP = {status.lower(): status for status in IP_STATUSES}


class ValidationError(ValueError):
    """Raised when one or more input fields fail validation."""

    def __init__(self, message: str, field_errors: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.field_errors = field_errors or {}


def normalize_ip_address(raw_ip: Any, field_name: str = "ip_address") -> str:
    """Validate and return canonical IPv4 or IPv6 address string."""
    if not isinstance(raw_ip, str) or not raw_ip.strip():
        raise ValidationError(
            f"{field_name} is required",
            {field_name: "IP address is required"},
        )
    candidate = raw_ip.strip()
    try:
        parsed = ipaddress.ip_address(candidate)
    except ValueError as exc:
        raise ValidationError(
            f"Invalid IPv4/IPv6 address: {candidate}",
            {field_name: "Must be a valid IPv4 or IPv6 address"},
        ) from exc
    return str(parsed)


def _clean_str(value: Any, max_len: int = 255) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        return str(value).strip()[:max_len]
    return value.strip()[:max_len]


def validate_ip_payload(payload: Any) -> dict[str, str]:
    """Validate and normalize a create/update Public IP payload."""
    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object")

    errors: dict[str, str] = {}
    cleaned: dict[str, str] = {}

    try:
        cleaned["ip_address"] = normalize_ip_address(payload.get("ip_address"), "ip_address")
    except ValidationError as exc:
        errors.update(exc.field_errors)

    provider = _clean_str(payload.get("provider"), 120)
    if not provider:
        errors["provider"] = "Provider is required"
    cleaned["provider"] = provider

    raw_owner = _clean_str(payload.get("owner_type"), 32)
    owner = _OWNER_LOOKUP.get(raw_owner.lower())
    if not owner:
        errors["owner_type"] = f"Owner must be one of: {', '.join(OWNER_TYPES)}"
    cleaned["owner_type"] = owner or raw_owner

    raw_status = _clean_str(payload.get("status"), 32)
    status = _STATUS_LOOKUP.get(raw_status.lower())
    if not status:
        errors["status"] = f"Status must be one of: {', '.join(IP_STATUSES)}"
    cleaned["status"] = status or raw_status

    raw_env = _clean_str(payload.get("environment"), 32)
    if raw_env:
        env = _ENV_LOOKUP.get(raw_env.lower())
        if not env:
            errors["environment"] = f"Environment must be one of: {', '.join(ENVIRONMENTS)}"
        cleaned["environment"] = env or raw_env
    else:
        if status == "Used":
            errors["environment"] = "Environment is required when status is Used"
        cleaned["environment"] = ""

    application = _clean_str(payload.get("application"), 150)
    if status == "Used" and not application:
        errors["application"] = "Application is required when status is Used"
    cleaned["application"] = application

    cleaned["domain"] = _clean_str(payload.get("domain"), 255)

    raw_server_ip = _clean_str(payload.get("server_ip"), 64)
    if raw_server_ip:
        try:
            cleaned["server_ip"] = normalize_ip_address(raw_server_ip, "server_ip")
        except ValidationError as exc:
            errors.update(exc.field_errors)
    else:
        cleaned["server_ip"] = ""

    cleaned["notes"] = _clean_str(payload.get("notes"), 2000)

    if errors:
        raise ValidationError("Validation failed", errors)

    return cleaned
