# Nginx UI – Public IP Inventory Plugin

Manual Public IP address inventory plugin (`com.company.public-ip-inventory`) for **Nginx UI v3.0.0**.

## Key Features

- **Dashboard**: Summary cards (Total IP, Used, Available, Reserved), IP utilization percentage, breakdowns by Provider, Owner (`Internal`/`External`), and Environment (`dev`/`staging`/`uat`/`prod`), plus recent audit activity.
- **IP Management**: Add, edit, view details (with per-IP audit history), and delete (with confirmation) Public IPv4 and IPv6 records.
- **Search & Filter**: Search across IP address, application, domain, server IP, provider, and notes; filter by Provider, Owner, Environment, and Status.
- **Reporting**: Aggregated reports by Provider, Owner, and Status, plus formula-safe CSV export.
- **SQLite Isolation & Backup**: Dedicated `public-ip-inventory.db` isolated from Nginx UI's internal database, with restrictive file permissions (`0600`/`0700`) and online SQLite backup/restore.

## Non-Goals (By Design)

- Does **not** modify Nginx configuration files.
- Does **not** perform automatic IP scanning, DNS discovery, or availability probing.
- All inventory updates are managed manually by authorized administrators.

## Project Structure

- `plugin.json` — Nginx UI v3.0.0 plugin manifest (`http` capability via Unix socket)
- `bin/public-ip-inventory-server` — Executable backend entrypoint
- `server/` — Python 3 stdlib backend (JSON-RPC 2.0 stdio, Unix/TCP HTTP router, SQLite repository, validation, online backup/restore)
- `webapp/` — Vue 3 + TypeScript + `@nginxui/plugin-sdk` + `antdv-next` frontend bundle
- `tests/` — Unit and integration test suite
- `scripts/` — Packaging (`package.sh`) and cron backup (`backup-db.sh`) scripts
- `docs/` — [Architecture](docs/ARCHITECTURE.md), [Installation](docs/INSTALLATION.md), and [Maintenance](docs/MAINTENANCE.md)

## Quick Verification

Run the backend test suite:

```bash
python3 -m unittest discover -s tests -v
```

Build frontend & package `.tar.gz` (requires Node.js and network access for `npm install` on first build):

```bash
npm --prefix webapp install
./scripts/package.sh
```
