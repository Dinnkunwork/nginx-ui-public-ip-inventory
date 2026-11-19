"""Tests for REST HTTP API over Unix socket, auth enforcement, delete confirmation, and CSV export."""

from __future__ import annotations

import http.client
import json
import socket
import tempfile
import unittest
from pathlib import Path

from server.config import Config
from server.db import DatabaseManager
from server.http_handler import InventoryRouter, start_unix_http_server
from server.repository import InventoryRepository


class UnixHTTPConnection(http.client.HTTPConnection):
    """HTTPConnection over a Unix domain socket."""

    def __init__(self, socket_path: str) -> None:
        super().__init__("localhost")
        self._socket_path = socket_path

    def connect(self) -> None:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self._socket_path)
        self.sock = sock


class TestHTTPAPI(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.config = Config(
            data_dir=base,
            db_path=base / "public-ip-inventory.db",
            backup_dir=base / "backups",
            socket_path=base / "http.sock",
            require_auth_header=True,
        )
        self.db = DatabaseManager(self.config)
        self.repo = InventoryRepository(self.db)
        self.router = InventoryRouter(self.config, self.db, self.repo)
        self.handle = start_unix_http_server(self.router, self.config.socket_path)

    def tearDown(self) -> None:
        self.handle.stop()
        self.tmp.cleanup()

    def _request(
        self,
        method: str,
        path: str,
        body: dict | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        conn = UnixHTTPConnection(str(self.config.socket_path))
        req_headers = dict(headers or {})
        raw = b""
        if body is not None:
            raw = json.dumps(body).encode("utf-8")
            req_headers["Content-Type"] = "application/json"
        conn.request(method, path, body=raw, headers=req_headers)
        resp = conn.getresponse()
        data = resp.read()
        resp_headers = {k.lower(): v for k, v in resp.getheaders()}
        conn.close()
        return resp.status, resp_headers, data

    def test_auth_required_except_health(self) -> None:
        status, _, _ = self._request("GET", "/health")
        self.assertEqual(status, 200)

        status, _, _ = self._request("GET", "/ips")
        self.assertEqual(status, 401)

    def test_full_crud_delete_confirm_and_csv_export(self) -> None:
        auth = {"X-Nginx-UI-User": "admin"}

        # Create IP
        status, _, data = self._request(
            "POST",
            "/ips",
            body={
                "ip_address": "103.55.10.1",
                "provider": "Biznet",
                "owner_type": "Internal",
                "application": "=SUM(1,1)",
                "environment": "prod",
                "status": "Used",
            },
            headers=auth,
        )
        self.assertEqual(status, 201)
        created = json.loads(data)
        ip_id = created["id"]

        # Duplicate returns 409
        status, _, _ = self._request(
            "POST",
            "/ips",
            body={
                "ip_address": "103.55.10.1",
                "provider": "Biznet",
                "owner_type": "Internal",
                "status": "Available",
            },
            headers=auth,
        )
        self.assertEqual(status, 409)

        # CSV export escapes formula-injection prefix '='
        status, headers, csv_data = self._request("GET", "/reports/export.csv", headers=auth)
        self.assertEqual(status, 200)
        self.assertIn("text/csv", headers["content-type"])
        csv_text = csv_data.decode("utf-8")
        self.assertIn("'=SUM(1,1)", csv_text)

        # Delete without confirm returns 400
        status, _, _ = self._request("DELETE", f"/ips/{ip_id}", headers=auth)
        self.assertEqual(status, 400)

        # Delete with confirm=true succeeds
        status, _, _ = self._request("DELETE", f"/ips/{ip_id}?confirm=true", headers=auth)
        self.assertEqual(status, 200)


if __name__ == "__main__":
    unittest.main()
