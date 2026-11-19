"""Integration tests for SQLite repository CRUD, search/filter, audit log, and backup/restore."""

from __future__ import annotations

import os
import stat
import tempfile
import unittest
from pathlib import Path

from server.config import Config
from server.db import DatabaseManager
from server.repository import DuplicateIPError, InventoryRepository, NotFoundError
from server.validation import validate_ip_payload


class TestRepository(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.config = Config(
            data_dir=base,
            db_path=base / "public-ip-inventory.db",
            backup_dir=base / "backups",
            socket_path=base / "http.sock",
            require_auth_header=False,
        )
        self.db = DatabaseManager(self.config)
        self.repo = InventoryRepository(self.db)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_db_permissions_are_restrictive(self) -> None:
        mode = stat.S_IMODE(os.stat(self.config.db_path).st_mode)
        self.assertEqual(mode, 0o600)

    def test_crud_duplicate_prevention_and_audit_log(self) -> None:
        created = self.repo.create_ip(
            validate_ip_payload(
                {
                    "ip_address": "103.10.20.10",
                    "provider": "Biznet",
                    "owner_type": "Internal",
                    "application": "Reconflower",
                    "domain": "reconflower.company.id",
                    "environment": "prod",
                    "server_ip": "10.10.1.10",
                    "status": "Used",
                    "notes": "Primary app",
                }
            ),
            actor="admin",
        )
        self.assertEqual(created["ip_address"], "103.10.20.10")
        self.assertEqual(len(created["audit_logs"]), 1)
        self.assertEqual(created["audit_logs"][0]["action"], "CREATE")

        # Duplicate IPv4 rejected
        with self.assertRaises(DuplicateIPError):
            self.repo.create_ip(
                validate_ip_payload(
                    {
                        "ip_address": "103.10.20.10",
                        "provider": "Telkom",
                        "owner_type": "External",
                        "status": "Available",
                    }
                ),
                actor="admin",
            )

        # Update
        updated = self.repo.update_ip(
            created["id"],
            validate_ip_payload(
                {
                    "ip_address": "103.10.20.10",
                    "provider": "Biznet",
                    "owner_type": "Internal",
                    "application": "Reconflower v2",
                    "domain": "reconflower.company.id",
                    "environment": "staging",
                    "server_ip": "10.10.1.11",
                    "status": "Reserved",
                    "notes": "Migrated",
                }
            ),
            actor="infra-lead",
        )
        self.assertEqual(updated["application"], "Reconflower v2")
        self.assertEqual(updated["status"], "Reserved")
        self.assertEqual(updated["audit_logs"][0]["action"], "UPDATE")

        # Delete
        deleted = self.repo.delete_ip(created["id"], actor="admin")
        self.assertTrue(deleted["deleted"])
        with self.assertRaises(NotFoundError):
            self.repo.get_ip(created["id"])

    def test_search_filters_and_dashboard_summary(self) -> None:
        samples = [
            {
                "ip_address": "103.10.20.10",
                "provider": "Biznet",
                "owner_type": "Internal",
                "application": "Reconflower",
                "environment": "prod",
                "status": "Used",
            },
            {
                "ip_address": "103.10.20.11",
                "provider": "Biznet",
                "owner_type": "External",
                "application": "Bangun Djaja",
                "environment": "prod",
                "status": "Used",
            },
            {
                "ip_address": "103.10.20.12",
                "provider": "Telkom",
                "owner_type": "Internal",
                "status": "Available",
            },
            {
                "ip_address": "2001:0db8::1",
                "provider": "AWS",
                "owner_type": "Internal",
                "application": "Huly",
                "environment": "staging",
                "status": "Reserved",
            },
        ]
        for s in samples:
            self.repo.create_ip(validate_ip_payload(s), actor="admin")

        summary = self.repo.get_dashboard_summary()
        self.assertEqual(summary["total"], 4)
        self.assertEqual(summary["used"], 2)
        self.assertEqual(summary["available"], 1)
        self.assertEqual(summary["reserved"], 1)
        self.assertEqual(summary["usage_percentage"], 50.0)

        # Search by IPv6 canonical form
        res_q = self.repo.list_ips(q="2001:db8::1")
        self.assertEqual(res_q["total"], 1)
        self.assertEqual(res_q["items"][0]["application"], "Huly")

        # Filter by provider + owner
        res_f = self.repo.list_ips(provider="Biznet", owner_type="External")
        self.assertEqual(res_f["total"], 1)
        self.assertEqual(res_f["items"][0]["application"], "Bangun Djaja")

    def test_backup_and_restore(self) -> None:
        rec = self.repo.create_ip(
            validate_ip_payload(
                {
                    "ip_address": "103.10.20.99",
                    "provider": "Biznet",
                    "owner_type": "Internal",
                    "status": "Available",
                }
            ),
            actor="admin",
        )
        backup = self.db.create_backup()
        self.assertIn(backup["filename"], [b["filename"] for b in self.db.list_backups()])

        # Delete record, then restore from backup
        self.repo.delete_ip(rec["id"], actor="admin")
        self.assertEqual(self.repo.get_dashboard_summary()["total"], 0)

        restore_res = self.db.restore_backup(backup["filename"])
        self.assertEqual(restore_res["restored_from"], backup["filename"])
        self.assertEqual(self.repo.get_dashboard_summary()["total"], 1)


if __name__ == "__main__":
    unittest.main()
