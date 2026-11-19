# Architecture & Database Design

## Overview

The plugin integrates with **Nginx UI v3.0.0** via the official Plugin System without modifying Nginx UI core source code:

1. **Manifest (`plugin.json`)**: Declares plugin ID `com.company.public-ip-inventory`, capability `http` (`listen: "unix"`), backend binary `bin/public-ip-inventory-server`, and frontend bundle `webapp/dist/main.js`.
2. **Backend (`server/`)**:
   - Communicates with Nginx UI over newline-delimited JSON-RPC 2.0 on `stdin`/`stdout` (`plugin.initialize`, `plugin.initialized`, `plugin.configure`, `plugin.ping`, `plugin.shutdown`, `plugin.exit`).
   - Serves the REST API on `$NGINX_UI_PLUGIN_DATA_DIR/http.sock` (mode `0600`). Nginx UI proxies authenticated requests from `/api/plugins/com.company.public-ip-inventory/http/*` and forwards the `X-Nginx-UI-User` header.
   - Uses Python 3 standard library (`sqlite3`, `ipaddress`, `http.server`, `csv`) with zero external runtime dependencies.
3. **Frontend (`webapp/`)**:
   - Built with `@nginxui/plugin-sdk` and `@nginxui/plugin-sdk/vite` so Vue 3, Vue Router, Pinia, and `antdv-next` are shared with the host Nginx UI SPA.
   - Registers 4 routes under the **Public IP Inventory** menu group: `Dashboard`, `IP Address List`, `Add IP Address`, and `Reports`.

## Database Schema (`public-ip-inventory.db`)

Default location: `/var/lib/nginx-ui/plugins/public-ip-inventory/public-ip-inventory.db` (or `$NGINX_UI_PLUGIN_DATA_DIR/public-ip-inventory.db` when managed by Nginx UI).

### `public_ips`

| Column | Type | Constraints |
|---|---|---|
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` |
| `ip_address` | `TEXT` | `NOT NULL UNIQUE` (canonical IPv4/IPv6) |
| `provider` | `TEXT` | `NOT NULL` |
| `owner_type` | `TEXT` | `NOT NULL CHECK (owner_type IN ('Internal', 'External'))` |
| `application` | `TEXT` | `NOT NULL DEFAULT ''` |
| `domain` | `TEXT` | `NOT NULL DEFAULT ''` |
| `environment` | `TEXT` | `NOT NULL DEFAULT '' CHECK (environment IN ('', 'dev', 'staging', 'uat', 'prod'))` |
| `server_ip` | `TEXT` | `NOT NULL DEFAULT ''` |
| `status` | `TEXT` | `NOT NULL CHECK (status IN ('Used', 'Available', 'Reserved'))` |
| `notes` | `TEXT` | `NOT NULL DEFAULT ''` |
| `created_at` | `DATETIME` | UTC ISO-8601 |
| `updated_at` | `DATETIME` | UTC ISO-8601 |

### `audit_logs`

Records `CREATE`, `UPDATE`, `DELETE`, `BACKUP`, and `RESTORE` events with `actor` (from `X-Nginx-UI-User`), `ip_id`, `ip_address`, `details_json`, and `created_at`.

## Security Controls

- All SQL queries use parameterized placeholders (`?`).
- Requests missing `X-Nginx-UI-User` (except `/health`) are rejected with `401 Unauthorized`.
- `DELETE /ips/{id}` requires explicit `confirm=true` / `{"confirm": true}`.
- CSV export neutralizes spreadsheet formula prefixes (`=`, `+`, `-`, `@`, `\t`, `\r`).
- Database directory is `0700` and SQLite files/backups are `0600`.
