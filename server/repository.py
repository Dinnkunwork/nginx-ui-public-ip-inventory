"""Repository layer for Public IP CRUD, search/filter, reporting, and audit logs."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from .db import DatabaseManager

SORTABLE_COLUMNS = {
    "id": "id",
    "ip_address": "ip_address",
    "provider": "provider",
    "owner_type": "owner_type",
    "application": "application",
    "environment": "environment",
    "status": "status",
    "created_at": "created_at",
    "updated_at": "updated_at",
}


class DuplicateIPError(ValueError):
    """Raised when attempting to store an IP address that already exists."""


class NotFoundError(LookupError):
    """Raised when a requested IP record does not exist."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


class InventoryRepository:
    """Data-access operations for public_ips and audit_logs using parameterized SQL."""

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def _record_audit(
        self,
        conn: sqlite3.Connection,
        action: str,
        actor: str,
        ip_id: int | None = None,
        ip_address: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        conn.execute(
            """
            INSERT INTO audit_logs (action, ip_id, ip_address, actor, details_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                action,
                ip_id,
                ip_address,
                actor or "system",
                json.dumps(details or {}, ensure_ascii=False),
                _now_iso(),
            ),
        )

    def _build_filter_clause(
        self,
        q: str = "",
        provider: str = "",
        owner_type: str = "",
        environment: str = "",
        status: str = "",
    ) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        params: list[Any] = []

        if q:
            like = f"%{q}%"
            clauses.append(
                "(ip_address LIKE ? OR provider LIKE ? OR application LIKE ? OR domain LIKE ? OR server_ip LIKE ? OR notes LIKE ?)"
            )
            params.extend([like, like, like, like, like, like])
        if provider:
            clauses.append("LOWER(provider) = LOWER(?)")
            params.append(provider)
        if owner_type:
            clauses.append("LOWER(owner_type) = LOWER(?)")
            params.append(owner_type)
        if environment:
            clauses.append("LOWER(environment) = LOWER(?)")
            params.append(environment)
        if status:
            clauses.append("LOWER(status) = LOWER(?)")
            params.append(status)

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        return where_sql, params

    def list_ips(
        self,
        *,
        q: str = "",
        provider: str = "",
        owner_type: str = "",
        environment: str = "",
        status: str = "",
        sort_by: str = "id",
        sort_dir: str = "desc",
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """List Public IPs with search, filters, sorting, and pagination."""
        where_sql, params = self._build_filter_clause(
            q=q,
            provider=provider,
            owner_type=owner_type,
            environment=environment,
            status=status,
        )
        sort_col = SORTABLE_COLUMNS.get(sort_by, "id")
        direction = "ASC" if str(sort_dir).lower() == "asc" else "DESC"
        page = max(1, page)
        page_size = max(1, min(500, page_size))
        offset = (page - 1) * page_size

        with self.db.connect() as conn:
            total = conn.execute(
                f"SELECT COUNT(*) AS cnt FROM public_ips {where_sql}",
                params,
            ).fetchone()["cnt"]

            rows = conn.execute(
                f"""
                SELECT id, ip_address, provider, owner_type, application, domain,
                       environment, server_ip, status, notes, created_at, updated_at
                FROM public_ips
                {where_sql}
                ORDER BY {sort_col} {direction}, id DESC
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            ).fetchall()

            providers = [
                r["provider"]
                for r in conn.execute(
                    "SELECT DISTINCT provider FROM public_ips WHERE provider != '' ORDER BY provider ASC"
                ).fetchall()
            ]

        return {
            "items": [_row_to_dict(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
            "providers": providers,
        }

    def export_ips(
        self,
        *,
        q: str = "",
        provider: str = "",
        owner_type: str = "",
        environment: str = "",
        status: str = "",
    ) -> list[dict[str, Any]]:
        """Return all matching Public IP records for CSV/report export."""
        where_sql, params = self._build_filter_clause(
            q=q,
            provider=provider,
            owner_type=owner_type,
            environment=environment,
            status=status,
        )
        with self.db.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, ip_address, provider, owner_type, application, domain,
                       environment, server_ip, status, notes, created_at, updated_at
                FROM public_ips
                {where_sql}
                ORDER BY ip_address ASC
                """,
                params,
            ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def get_ip(self, ip_id: int) -> dict[str, Any]:
        """Fetch a single IP record and its recent audit logs."""
        with self.db.connect() as conn:
            row = conn.execute(
                """
                SELECT id, ip_address, provider, owner_type, application, domain,
                       environment, server_ip, status, notes, created_at, updated_at
                FROM public_ips WHERE id = ?
                """,
                (ip_id,),
            ).fetchone()
            if not row:
                raise NotFoundError(f"Public IP record {ip_id} not found")

            audits = conn.execute(
                """
                SELECT id, action, ip_id, ip_address, actor, details_json, created_at
                FROM audit_logs
                WHERE ip_id = ?
                ORDER BY id DESC
                LIMIT 25
                """,
                (ip_id,),
            ).fetchall()

        result = _row_to_dict(row)
        result["audit_logs"] = [
            {**_row_to_dict(a), "details": json.loads(a["details_json"] or "{}")} for a in audits
        ]
        return result

    def create_ip(self, data: dict[str, str], actor: str) -> dict[str, Any]:
        """Insert a new Public IP record, preventing duplicates."""
        now = _now_iso()
        with self.db.connect() as conn:
            try:
                cur = conn.execute(
                    """
                    INSERT INTO public_ips (
                        ip_address, provider, owner_type, application, domain,
                        environment, server_ip, status, notes, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        data["ip_address"],
                        data["provider"],
                        data["owner_type"],
                        data["application"],
                        data["domain"],
                        data["environment"],
                        data["server_ip"],
                        data["status"],
                        data["notes"],
                        now,
                        now,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                if "UNIQUE" in str(exc).upper():
                    raise DuplicateIPError(f"IP address {data['ip_address']} already exists") from exc
                raise

            ip_id = int(cur.lastrowid)
            self._record_audit(
                conn,
                action="CREATE",
                actor=actor,
                ip_id=ip_id,
                ip_address=data["ip_address"],
                details={"after": data},
            )
            conn.commit()
        return self.get_ip(ip_id)

    def update_ip(self, ip_id: int, data: dict[str, str], actor: str) -> dict[str, Any]:
        """Update an existing Public IP record, preventing duplicate IP addresses."""
        now = _now_iso()
        with self.db.connect() as conn:
            existing = conn.execute(
                """
                SELECT id, ip_address, provider, owner_type, application, domain,
                       environment, server_ip, status, notes
                FROM public_ips WHERE id = ?
                """,
                (ip_id,),
            ).fetchone()
            if not existing:
                raise NotFoundError(f"Public IP record {ip_id} not found")

            try:
                conn.execute(
                    """
                    UPDATE public_ips
                    SET ip_address = ?, provider = ?, owner_type = ?, application = ?,
                        domain = ?, environment = ?, server_ip = ?, status = ?,
                        notes = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        data["ip_address"],
                        data["provider"],
                        data["owner_type"],
                        data["application"],
                        data["domain"],
                        data["environment"],
                        data["server_ip"],
                        data["status"],
                        data["notes"],
                        now,
                        ip_id,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                if "UNIQUE" in str(exc).upper():
                    raise DuplicateIPError(f"IP address {data['ip_address']} already exists") from exc
                raise

            self._record_audit(
                conn,
                action="UPDATE",
                actor=actor,
                ip_id=ip_id,
                ip_address=data["ip_address"],
                details={"before": _row_to_dict(existing), "after": data},
            )
            conn.commit()
        return self.get_ip(ip_id)

    def delete_ip(self, ip_id: int, actor: str) -> dict[str, Any]:
        """Delete an IP record and log the deletion."""
        with self.db.connect() as conn:
            existing = conn.execute(
                """
                SELECT id, ip_address, provider, owner_type, application, domain,
                       environment, server_ip, status, notes
                FROM public_ips WHERE id = ?
                """,
                (ip_id,),
            ).fetchone()
            if not existing:
                raise NotFoundError(f"Public IP record {ip_id} not found")

            conn.execute("DELETE FROM public_ips WHERE id = ?", (ip_id,))
            self._record_audit(
                conn,
                action="DELETE",
                actor=actor,
                ip_id=ip_id,
                ip_address=existing["ip_address"],
                details={"deleted": _row_to_dict(existing)},
            )
            conn.commit()
        return {"deleted": True, "id": ip_id, "ip_address": existing["ip_address"]}

    def get_dashboard_summary(self) -> dict[str, Any]:
        """Return summary counts, usage percentage, and grouped breakdowns."""
        with self.db.connect() as conn:
            counts_row = conn.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    COALESCE(SUM(CASE WHEN status = 'Used' THEN 1 ELSE 0 END), 0) AS used,
                    COALESCE(SUM(CASE WHEN status = 'Available' THEN 1 ELSE 0 END), 0) AS available,
                    COALESCE(SUM(CASE WHEN status = 'Reserved' THEN 1 ELSE 0 END), 0) AS reserved
                FROM public_ips
                """
            ).fetchone()

            by_provider = [
                _row_to_dict(r)
                for r in conn.execute(
                    """
                    SELECT provider,
                           COUNT(*) AS total,
                           SUM(CASE WHEN status = 'Used' THEN 1 ELSE 0 END) AS used,
                           SUM(CASE WHEN status = 'Available' THEN 1 ELSE 0 END) AS available,
                           SUM(CASE WHEN status = 'Reserved' THEN 1 ELSE 0 END) AS reserved
                    FROM public_ips
                    GROUP BY provider
                    ORDER BY total DESC, provider ASC
                    """
                ).fetchall()
            ]

            by_owner = [
                _row_to_dict(r)
                for r in conn.execute(
                    """
                    SELECT owner_type,
                           COUNT(*) AS total,
                           SUM(CASE WHEN status = 'Used' THEN 1 ELSE 0 END) AS used,
                           SUM(CASE WHEN status = 'Available' THEN 1 ELSE 0 END) AS available,
                           SUM(CASE WHEN status = 'Reserved' THEN 1 ELSE 0 END) AS reserved
                    FROM public_ips
                    GROUP BY owner_type
                    ORDER BY total DESC
                    """
                ).fetchall()
            ]

            by_environment = [
                _row_to_dict(r)
                for r in conn.execute(
                    """
                    SELECT CASE WHEN environment = '' THEN 'unassigned' ELSE environment END AS environment,
                           COUNT(*) AS total
                    FROM public_ips
                    GROUP BY environment
                    ORDER BY total DESC
                    """
                ).fetchall()
            ]

            recent_audits = [
                {**_row_to_dict(r), "details": json.loads(r["details_json"] or "{}")}
                for r in conn.execute(
                    """
                    SELECT id, action, ip_id, ip_address, actor, details_json, created_at
                    FROM audit_logs
                    ORDER BY id DESC
                    LIMIT 10
                    """
                ).fetchall()
            ]

        total = int(counts_row["total"])
        used = int(counts_row["used"])
        available = int(counts_row["available"])
        reserved = int(counts_row["reserved"])
        usage_percentage = round((used / total) * 100, 2) if total > 0 else 0.0

        return {
            "total": total,
            "used": used,
            "available": available,
            "reserved": reserved,
            "usage_percentage": usage_percentage,
            "by_provider": by_provider,
            "by_owner": by_owner,
            "by_environment": by_environment,
            "recent_audits": recent_audits,
        }

    def list_audit_logs(self, page: int = 1, page_size: int = 50) -> dict[str, Any]:
        """Return paginated audit log entries."""
        page = max(1, page)
        page_size = max(1, min(200, page_size))
        offset = (page - 1) * page_size
        with self.db.connect() as conn:
            total = conn.execute("SELECT COUNT(*) AS cnt FROM audit_logs").fetchone()["cnt"]
            rows = conn.execute(
                """
                SELECT id, action, ip_id, ip_address, actor, details_json, created_at
                FROM audit_logs
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (page_size, offset),
            ).fetchall()
        return {
            "items": [{**_row_to_dict(r), "details": json.loads(r["details_json"] or "{}")} for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def log_system_event(self, action: str, actor: str, details: dict[str, Any]) -> None:
        """Record a non-IP-specific audit event such as BACKUP or RESTORE."""
        with self.db.connect() as conn:
            self._record_audit(conn, action=action, actor=actor, details=details)
            conn.commit()
