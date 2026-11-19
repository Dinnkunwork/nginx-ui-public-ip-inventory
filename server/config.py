"""Configuration and domain constants for the Public IP Inventory plugin."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PLUGIN_ID = "com.company.public-ip-inventory"
PLUGIN_NAME = "Public IP Inventory"
PLUGIN_VERSION = "1.0.0"
API_VERSION = 1

DEFAULT_DATA_DIR = "/var/lib/nginx-ui/plugins/public-ip-inventory"
DB_FILENAME = "public-ip-inventory.db"
SOCKET_FILENAME = "http.sock"

OWNER_TYPES = ("Internal", "External")
ENVIRONMENTS = ("dev", "staging", "uat", "prod")
IP_STATUSES = ("Used", "Available", "Reserved")


@dataclass
class Config:
    """Runtime configuration resolved from environment and plugin settings."""

    data_dir: Path
    db_path: Path
    backup_dir: Path
    socket_path: Path
    require_auth_header: bool = True

    @classmethod
    def from_env(cls, settings: dict[str, Any] | None = None) -> "Config":
        """Build configuration from environment variables and optional plugin settings."""
        settings = settings or {}
        env_data_dir = os.environ.get("NGINX_UI_PLUGIN_DATA_DIR", "").strip()
        data_dir = Path(env_data_dir or DEFAULT_DATA_DIR)

        db_override = (
            str(settings.get("db_path") or "").strip()
            or os.environ.get("IP_INVENTORY_DB_PATH", "").strip()
        )
        db_path = Path(db_override) if db_override else data_dir / DB_FILENAME

        backup_override = (
            str(settings.get("backup_dir") or "").strip()
            or os.environ.get("IP_INVENTORY_BACKUP_DIR", "").strip()
        )
        backup_dir = Path(backup_override) if backup_override else db_path.parent / "backups"

        socket_path = data_dir / SOCKET_FILENAME
        require_auth = os.environ.get("IP_INVENTORY_REQUIRE_AUTH", "1").strip() != "0"

        return cls(
            data_dir=data_dir,
            db_path=db_path,
            backup_dir=backup_dir,
            socket_path=socket_path,
            require_auth_header=require_auth,
        )
