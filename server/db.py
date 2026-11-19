"""SQLite database management, schema initialization, permissions, and backup/restore."""

from __future__ import annotations

import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import Config

_BACKUP_NAME_RE = re.compile(r"^public-ip-inventory-[A-Za-z0-9_.-]+\.db$")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS public_ips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_address TEXT NOT NULL UNIQUE,
    provider TEXT NOT NULL,
    owner_type TEXT NOT NULL CHECK (owner_type IN ('Internal', 'External')),
    application TEXT NOT NULL DEFAULT '',
    domain TEXT NOT NULL DEFAULT '',
    environment TEXT NOT NULL DEFAULT '' CHECK (environment IN ('', 'dev', 'staging', 'uat', 'prod')),
    server_ip TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL CHECK (status IN ('Used', 'Available', 'Reserved')),
    notes TEXT NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_public_ips_status ON public_ips(status);
CREATE INDEX IF NOT EXISTS idx_public_ips_owner_type ON public_ips(owner_type);
CREATE INDEX IF NOT EXISTS idx_public_ips_environment ON public_ips(environment);
CREATE INDEX IF NOT EXISTS idx_public_ips_provider ON public_ips(provider);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    ip_id INTEGER,
    ip_address TEXT NOT NULL DEFAULT '',
    actor TEXT NOT NULL DEFAULT 'system',
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_ip_id ON audit_logs(ip_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at DESC);
"""


def _ensure_secure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass


def _ensure_secure_file(path: Path) -> None:
    if path.exists():
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass


class DatabaseManager:
    """Manages SQLite connections, schema setup, file permissions, and online backups."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.initialize()

    def initialize(self) -> None:
        """Create directories, initialize schema, and enforce restrictive permissions."""
        _ensure_secure_dir(self.config.db_path.parent)
        _ensure_secure_dir(self.config.backup_dir)
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()
        _ensure_secure_file(self.config.db_path)

    def connect(self) -> sqlite3.Connection:
        """Open a SQLite connection configured with WAL mode and row factory."""
        conn = sqlite3.connect(str(self.config.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    def create_backup(self, tag: str = "") -> dict[str, Any]:
        """Create a consistent online SQLite backup using sqlite3.Connection.backup()."""
        _ensure_secure_dir(self.config.backup_dir)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        suffix = f"-{re.sub(r'[^a-zA-Z0-9_-]', '', tag)}" if tag else ""
        filename = f"public-ip-inventory-{stamp}{suffix}.db"
        dest_path = self.config.backup_dir / filename

        # Avoid overwriting if two backups happen within the same second
        counter = 1
        while dest_path.exists():
            filename = f"public-ip-inventory-{stamp}{suffix}-{counter}.db"
            dest_path = self.config.backup_dir / filename
            counter += 1

        with self.connect() as src_conn:
            with sqlite3.connect(str(dest_path)) as dst_conn:
                src_conn.backup(dst_conn)
        _ensure_secure_file(dest_path)

        stat = dest_path.stat()
        return {
            "filename": filename,
            "size_bytes": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    def list_backups(self) -> list[dict[str, Any]]:
        """Return metadata for all backups sorted newest first."""
        if not self.config.backup_dir.exists():
            return []
        items: list[dict[str, Any]] = []
        for entry in self.config.backup_dir.iterdir():
            if entry.is_file() and _BACKUP_NAME_RE.match(entry.name):
                stat = entry.stat()
                items.append(
                    {
                        "filename": entry.name,
                        "size_bytes": stat.st_size,
                        "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).strftime(
                            "%Y-%m-%dT%H:%M:%SZ"
                        ),
                    }
                )
        items.sort(key=lambda item: item["filename"], reverse=True)
        return items

    def restore_backup(self, filename: str) -> dict[str, Any]:
        """Restore the active database from a validated backup file after taking a safety snapshot."""
        if not filename or Path(filename).name != filename or not _BACKUP_NAME_RE.match(filename):
            raise ValueError("Invalid backup filename")

        src_path = self.config.backup_dir / filename
        if not src_path.is_file():
            raise FileNotFoundError(f"Backup file not found: {filename}")

        safety_backup = self.create_backup(tag="pre-restore")

        with sqlite3.connect(str(src_path)) as src_conn:
            with self.connect() as dst_conn:
                src_conn.backup(dst_conn)
                dst_conn.executescript(SCHEMA_SQL)
                dst_conn.commit()
        _ensure_secure_file(self.config.db_path)

        return {
            "restored_from": filename,
            "safety_backup": safety_backup["filename"],
        }
