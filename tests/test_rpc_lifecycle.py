"""Tests for Nginx UI v3.0.0 JSON-RPC 2.0 plugin lifecycle and http.handle."""

from __future__ import annotations

import base64
import io
import json
import tempfile
import unittest
from pathlib import Path

from server.config import Config
from server.rpc import PluginRPCServer


class TestRPCLifecycle(unittest.TestCase):
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

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_initialize_ping_http_handle_and_shutdown(self) -> None:
        requests = [
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "plugin.initialize",
                    "params": {"host": {"version": "3.0.0"}, "settings": {}},
                }
            ),
            json.dumps({"jsonrpc": "2.0", "method": "plugin.initialized", "params": {}}),
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "plugin.ping", "params": {}}),
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "http.handle",
                    "params": {
                        "method": "GET",
                        "path": "/dashboard/summary",
                        "headers": {"X-Nginx-UI-User": "admin"},
                    },
                }
            ),
            json.dumps({"jsonrpc": "2.0", "id": 4, "method": "plugin.shutdown", "params": {}}),
        ]
        stdin = io.StringIO("\n".join(requests) + "\n")
        stdout = io.StringIO()

        rpc = PluginRPCServer(self.config, stdin=stdin, stdout=stdout, start_http=False)
        rpc.serve_forever()

        lines = [json.loads(line) for line in stdout.getvalue().strip().splitlines()]
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[0]["result"]["capabilities"], ["http"])
        self.assertEqual(lines[1]["result"]["ok"], True)
        self.assertEqual(lines[2]["result"]["status"], 200)
        summary = json.loads(base64.b64decode(lines[2]["result"]["body_base64"]).decode("utf-8"))
        self.assertEqual(summary["total"], 0)
        self.assertEqual(lines[3]["result"]["ok"], True)


if __name__ == "__main__":
    unittest.main()
