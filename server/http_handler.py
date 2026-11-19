"""HTTP API router and Unix/TCP server adapters for the Public IP Inventory plugin."""

from __future__ import annotations

import base64
import csv
import io
import json
import os
import socket
import socketserver
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .config import PLUGIN_ID, PLUGIN_VERSION, Config
from .db import DatabaseManager
from .repository import DuplicateIPError, InventoryRepository, NotFoundError
from .validation import ValidationError, validate_ip_payload

_CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _safe_csv_cell(value: Any) -> str:
    text = "" if value is None else str(value)
    if text.startswith(_CSV_FORMULA_PREFIXES):
        return f"'{text}"
    return text


def _json_response(status: int, payload: Any) -> tuple[int, dict[str, str], bytes]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return (
        status,
        {
            "Content-Type": "application/json; charset=utf-8",
            "Content-Length": str(len(body)),
            "Cache-Control": "no-store",
        },
        body,
    )


class InventoryRouter:
    """Transport-agnostic HTTP request dispatcher for the inventory REST API."""

    def __init__(self, config: Config, db: DatabaseManager, repo: InventoryRepository) -> None:
        self.config = config
        self.db = db
        self.repo = repo

    def _extract_actor(self, headers: dict[str, str]) -> str | None:
        lowered = {k.lower(): v for k, v in headers.items()}
        user = (
            lowered.get("x-nginx-ui-user")
            or lowered.get("x-nginx-ui-username")
            or lowered.get("x-nginx-ui-user-name")
            or lowered.get("x-nginxui-user")
            or lowered.get("x-forwarded-user")
            or ""
        ).strip()
        if user:
            return user
        if not self.config.require_auth_header:
            return "nginx-ui"
        return None

    def dispatch(
        self,
        method: str,
        raw_path: str,
        headers: dict[str, str] | None = None,
        body: bytes = b"",
    ) -> tuple[int, dict[str, str], bytes]:
        """Dispatch an HTTP request and return (status_code, headers, response_bytes)."""
        headers = headers or {}
        parsed = urlparse(raw_path)
        path = parsed.path or "/"
        # Strip optional Nginx UI proxy prefix if forwarded unstripped
        prefix = f"/api/plugins/{PLUGIN_ID}/http"
        if path.startswith(prefix):
            path = path[len(prefix) :] or "/"
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")

        query = {k: v[0] if v else "" for k, v in parse_qs(parsed.query, keep_blank_values=True).items()}

        if method == "GET" and path == "/health":
            return _json_response(
                HTTPStatus.OK,
                {"status": "ok", "plugin": PLUGIN_ID, "version": PLUGIN_VERSION},
            )

        actor = self._extract_actor(headers)
        if actor is None:
            return _json_response(
                HTTPStatus.UNAUTHORIZED,
                {"error": "Unauthorized: missing Nginx UI authenticated user context"},
            )

        try:
            return self._route_authenticated(method, path, query, body, actor)
        except ValidationError as exc:
            return _json_response(
                HTTPStatus.BAD_REQUEST,
                {"error": exc.message, "field_errors": exc.field_errors},
            )
        except DuplicateIPError as exc:
            return _json_response(HTTPStatus.CONFLICT, {"error": str(exc)})
        except NotFoundError as exc:
            return _json_response(HTTPStatus.NOT_FOUND, {"error": str(exc)})
        except FileNotFoundError as exc:
            return _json_response(HTTPStatus.NOT_FOUND, {"error": str(exc)})
        except ValueError as exc:
            return _json_response(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except Exception as exc:  # pragma: no cover - defensive fallback
            return _json_response(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": f"Internal server error: {exc}"},
            )

    def _parse_json_body(self, body: bytes) -> dict[str, Any]:
        if not body:
            return {}
        try:
            data = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValidationError("Invalid JSON request body") from exc
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")
        return data

    def _route_authenticated(
        self,
        method: str,
        path: str,
        query: dict[str, str],
        body: bytes,
        actor: str,
    ) -> tuple[int, dict[str, str], bytes]:
        if method == "GET" and path == "/dashboard/summary":
            return _json_response(HTTPStatus.OK, self.repo.get_dashboard_summary())

        if method == "GET" and path == "/ips":
            page = int(query.get("page") or 1)
            page_size = int(query.get("page_size") or 50)
            result = self.repo.list_ips(
                q=query.get("q", "").strip(),
                provider=query.get("provider", "").strip(),
                owner_type=query.get("owner_type", "").strip(),
                environment=query.get("environment", "").strip(),
                status=query.get("status", "").strip(),
                sort_by=query.get("sort_by", "id").strip(),
                sort_dir=query.get("sort_dir", "desc").strip(),
                page=page,
                page_size=page_size,
            )
            return _json_response(HTTPStatus.OK, result)

        if method == "POST" and path == "/ips":
            payload = self._parse_json_body(body)
            cleaned = validate_ip_payload(payload)
            created = self.repo.create_ip(cleaned, actor=actor)
            return _json_response(HTTPStatus.CREATED, created)

        if path.startswith("/ips/"):
            id_part = path[len("/ips/") :]
            if not id_part.isdigit():
                raise NotFoundError("Invalid IP record ID")
            ip_id = int(id_part)

            if method == "GET":
                return _json_response(HTTPStatus.OK, self.repo.get_ip(ip_id))
            if method == "PUT":
                payload = self._parse_json_body(body)
                cleaned = validate_ip_payload(payload)
                updated = self.repo.update_ip(ip_id, cleaned, actor=actor)
                return _json_response(HTTPStatus.OK, updated)
            if method == "DELETE":
                payload = self._parse_json_body(body) if body else {}
                confirmed = query.get("confirm", "").lower() == "true" or payload.get("confirm") is True
                if not confirmed:
                    raise ValidationError(
                        "Deletion requires explicit confirmation (confirm=true)",
                        {"confirm": "Confirmation is required before deleting an IP record"},
                    )
                return _json_response(HTTPStatus.OK, self.repo.delete_ip(ip_id, actor=actor))

        if method == "GET" and path == "/reports/summary":
            return _json_response(HTTPStatus.OK, self.repo.get_dashboard_summary())

        if method == "GET" and path == "/reports/export.csv":
            rows = self.repo.export_ips(
                q=query.get("q", "").strip(),
                provider=query.get("provider", "").strip(),
                owner_type=query.get("owner_type", "").strip(),
                environment=query.get("environment", "").strip(),
                status=query.get("status", "").strip(),
            )
            csv_bytes = self._render_csv(rows)
            return (
                HTTPStatus.OK,
                {
                    "Content-Type": "text/csv; charset=utf-8",
                    "Content-Disposition": 'attachment; filename="public-ip-inventory.csv"',
                    "Content-Length": str(len(csv_bytes)),
                    "Cache-Control": "no-store",
                },
                csv_bytes,
            )

        if method == "GET" and path == "/audit-logs":
            page = int(query.get("page") or 1)
            page_size = int(query.get("page_size") or 50)
            return _json_response(HTTPStatus.OK, self.repo.list_audit_logs(page=page, page_size=page_size))

        if method == "GET" and path == "/backups":
            return _json_response(HTTPStatus.OK, {"items": self.db.list_backups()})

        if method == "POST" and path == "/backups":
            backup = self.db.create_backup()
            self.repo.log_system_event("BACKUP", actor=actor, details=backup)
            return _json_response(HTTPStatus.CREATED, backup)

        if method == "POST" and path == "/backups/restore":
            payload = self._parse_json_body(body)
            filename = str(payload.get("filename") or "").strip()
            if payload.get("confirm") is not True:
                raise ValidationError(
                    "Restore requires explicit confirmation",
                    {"confirm": "Confirmation is required before restoring a backup"},
                )
            result = self.db.restore_backup(filename)
            self.repo.log_system_event("RESTORE", actor=actor, details=result)
            return _json_response(HTTPStatus.OK, result)

        return _json_response(HTTPStatus.NOT_FOUND, {"error": f"Route not found: {method} {path}"})

    @staticmethod
    def _render_csv(rows: list[dict[str, Any]]) -> bytes:
        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="\n")
        headers = [
            "id",
            "ip_address",
            "provider",
            "owner_type",
            "application",
            "domain",
            "environment",
            "server_ip",
            "status",
            "notes",
            "created_at",
            "updated_at",
        ]
        writer.writerow(headers)
        for row in rows:
            writer.writerow([_safe_csv_cell(row.get(col, "")) for col in headers])
        return buf.getvalue().encode("utf-8")


def _make_handler_class(router: InventoryRouter) -> type[BaseHTTPRequestHandler]:
    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            # Keep stdout clean for JSON-RPC 2.0 traffic
            return

        def _handle(self, method: str) -> None:
            content_length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(content_length) if content_length > 0 else b""
            req_headers = {k: v for k, v in self.headers.items()}
            status, resp_headers, resp_body = router.dispatch(method, self.path, req_headers, body)
            self.send_response(status)
            for key, val in resp_headers.items():
                self.send_header(key, val)
            self.end_headers()
            if resp_body:
                self.wfile.write(resp_body)

        def do_GET(self) -> None:  # noqa: N802
            self._handle("GET")

        def do_POST(self) -> None:  # noqa: N802
            self._handle("POST")

        def do_PUT(self) -> None:  # noqa: N802
            self._handle("PUT")

        def do_DELETE(self) -> None:  # noqa: N802
            self._handle("DELETE")

    return _Handler


class ThreadingUnixHTTPServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    """Threaded Unix domain socket HTTP server."""

    daemon_threads = True
    allow_reuse_address = True


class HTTPServerHandle:
    """Manages background Unix socket or TCP HTTP server lifecycle."""

    def __init__(self, server: socketserver.BaseServer, socket_path: Path | None = None) -> None:
        self._server = server
        self._socket_path = socket_path
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        if self._socket_path and self._socket_path.exists():
            try:
                self._socket_path.unlink()
            except OSError:
                pass


def start_unix_http_server(router: InventoryRouter, socket_path: Path) -> HTTPServerHandle:
    """Start the HTTP API server on a Unix domain socket with 0600 permissions."""
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    if socket_path.exists():
        socket_path.unlink()

    handler_cls = _make_handler_class(router)
    server = ThreadingUnixHTTPServer(str(socket_path), handler_cls)
    try:
        os.chmod(socket_path, 0o600)
    except OSError:
        pass
    handle = HTTPServerHandle(server, socket_path=socket_path)
    handle.start()
    return handle


def start_tcp_http_server(router: InventoryRouter, host: str, port: int) -> HTTPServerHandle:
    """Start a TCP HTTP server (used for local development and testing)."""
    handler_cls = _make_handler_class(router)
    server = ThreadingHTTPServer((host, port), handler_cls)
    handle = HTTPServerHandle(server)
    handle.start()
    return handle


def encode_rpc_http_response(status: int, headers: dict[str, str], body: bytes) -> dict[str, Any]:
    """Encode an HTTP response for JSON-RPC http.handle mode."""
    return {
        "status": status,
        "headers": headers,
        "body_base64": base64.b64encode(body).decode("ascii"),
    }
