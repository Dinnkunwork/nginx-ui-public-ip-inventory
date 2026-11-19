"""JSON-RPC 2.0 stdio transport for Nginx UI v3.0.0 plugin lifecycle and RPC HTTP."""

from __future__ import annotations

import base64
import json
import sys
from typing import Any, Callable, TextIO

from .config import API_VERSION, Config
from .db import DatabaseManager
from .http_handler import HTTPServerHandle, InventoryRouter, encode_rpc_http_response, start_unix_http_server
from .repository import InventoryRepository


class PluginRPCServer:
    """Handles newline-delimited JSON-RPC 2.0 messages on stdin/stdout."""

    def __init__(
        self,
        config: Config,
        stdin: TextIO | None = None,
        stdout: TextIO | None = None,
        start_http: bool = True,
    ) -> None:
        self.config = config
        self.stdin = stdin or sys.stdin
        self.stdout = stdout or sys.stdout
        self.start_http = start_http
        self.db = DatabaseManager(config)
        self.repo = InventoryRepository(self.db)
        self.router = InventoryRouter(config, self.db, self.repo)
        self.http_handle: HTTPServerHandle | None = None
        self.should_exit = False

    def _write_message(self, payload: dict[str, Any]) -> None:
        self.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self.stdout.flush()

    def _reply_result(self, req_id: Any, result: Any) -> None:
        self._write_message({"jsonrpc": "2.0", "id": req_id, "result": result})

    def _reply_error(self, req_id: Any, code: int, message: str) -> None:
        self._write_message(
            {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}
        )

    def _apply_settings(self, settings: dict[str, Any] | None) -> None:
        if not settings:
            return
        updated = Config.from_env(settings)
        if updated.db_path != self.config.db_path or updated.backup_dir != self.config.backup_dir:
            self.config = updated
            self.db = DatabaseManager(updated)
            self.repo = InventoryRepository(self.db)
            self.router = InventoryRouter(updated, self.db, self.repo)

    def handle_message(self, raw_line: str) -> None:
        """Process a single JSON-RPC 2.0 request or notification line."""
        line = raw_line.strip()
        if not line:
            return
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            self._reply_error(None, -32700, "Parse error")
            return

        req_id = msg.get("id")
        method = msg.get("method", "")
        params = msg.get("params") or {}

        handlers: dict[str, Callable[[dict[str, Any]], Any]] = {
            "plugin.initialize": self._on_initialize,
            "plugin.configure": self._on_configure,
            "plugin.ping": self._on_ping,
            "plugin.shutdown": self._on_shutdown,
            "http.handle": self._on_http_handle,
        }

        if method == "plugin.initialized":
            return
        if method == "plugin.exit":
            self.stop()
            return

        handler = handlers.get(method)
        if handler is None:
            if req_id is not None:
                self._reply_error(req_id, -32601, f"Method not found: {method}")
            return

        try:
            result = handler(params)
            if req_id is not None:
                self._reply_result(req_id, result)
        except Exception as exc:  # pragma: no cover - defensive RPC boundary
            if req_id is not None:
                self._reply_error(req_id, -32603, str(exc))

    def _on_initialize(self, params: dict[str, Any]) -> dict[str, Any]:
        settings = params.get("settings")
        if isinstance(settings, dict):
            self._apply_settings(settings)
        if self.start_http and self.http_handle is None:
            self.http_handle = start_unix_http_server(self.router, self.config.socket_path)
        return {
            "api_version": API_VERSION,
            "capabilities": ["http"],
        }

    def _on_configure(self, params: dict[str, Any]) -> dict[str, Any]:
        settings = params.get("settings")
        if isinstance(settings, dict):
            self._apply_settings(settings)
        return {"ok": True}

    def _on_ping(self, _params: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True}

    def _on_shutdown(self, _params: dict[str, Any]) -> dict[str, Any]:
        self.stop()
        return {"ok": True}

    def _on_http_handle(self, params: dict[str, Any]) -> dict[str, Any]:
        method = str(params.get("method") or "GET").upper()
        path = str(params.get("path") or "/")
        headers = params.get("headers") if isinstance(params.get("headers"), dict) else {}
        raw_body = b""
        if isinstance(params.get("body_base64"), str) and params["body_base64"]:
            raw_body = base64.b64decode(params["body_base64"])
        elif isinstance(params.get("body"), str):
            raw_body = params["body"].encode("utf-8")
        status, resp_headers, resp_body = self.router.dispatch(method, path, headers, raw_body)
        return encode_rpc_http_response(status, resp_headers, resp_body)

    def stop(self) -> None:
        """Stop HTTP server and signal the stdio loop to exit."""
        if self.http_handle is not None:
            self.http_handle.stop()
            self.http_handle = None
        self.should_exit = True

    def serve_forever(self) -> None:
        """Read newline-delimited JSON-RPC messages until EOF or shutdown."""
        try:
            for line in self.stdin:
                self.handle_message(line)
                if self.should_exit:
                    break
        finally:
            self.stop()
