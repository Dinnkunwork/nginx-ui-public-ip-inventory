"""CLI entrypoint for the Nginx UI Public IP Inventory plugin backend."""

from __future__ import annotations

import argparse
import signal
import sys
import time

from .config import Config
from .db import DatabaseManager
from .http_handler import InventoryRouter, start_tcp_http_server
from .repository import InventoryRepository
from .rpc import PluginRPCServer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Nginx UI Public IP Inventory Plugin Server")
    parser.add_argument(
        "--listen-tcp",
        default="",
        help="Optional host:port to run standalone HTTP server for local development (disables stdio RPC)",
    )
    parser.add_argument(
        "--no-auth",
        action="store_true",
        help="Disable X-Nginx-UI-User header requirement in standalone dev mode",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create a safe SQLite online backup and exit",
    )
    args = parser.parse_args(argv)

    config = Config.from_env()
    if args.no_auth:
        config.require_auth_header = False

    if args.backup:
        db = DatabaseManager(config)
        result = db.create_backup()
        print(f"Backup created: {config.backup_dir / result['filename']} ({result['size_bytes']} bytes)")
        return 0

    if args.listen_tcp:
        host, _, port_str = args.listen_tcp.rpartition(":")
        host = host or "127.0.0.1"
        port = int(port_str or "8099")
        db = DatabaseManager(config)
        repo = InventoryRepository(db)
        router = InventoryRouter(config, db, repo)
        handle = start_tcp_http_server(router, host, port)
        print(f"Public IP Inventory HTTP server listening on http://{host}:{port}", file=sys.stderr)

        stop = False

        def _on_sig(_signum: int, _frame: object) -> None:
            nonlocal stop
            stop = True

        signal.signal(signal.SIGINT, _on_sig)
        signal.signal(signal.SIGTERM, _on_sig)
        try:
            while not stop:
                time.sleep(0.2)
        finally:
            handle.stop()
        return 0

    rpc_server = PluginRPCServer(config)

    def _on_term(_signum: int, _frame: object) -> None:
        rpc_server.stop()

    signal.signal(signal.SIGINT, _on_term)
    signal.signal(signal.SIGTERM, _on_term)
    rpc_server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
