#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export NGINX_UI_PLUGIN_DATA_DIR="${NGINX_UI_PLUGIN_DATA_DIR:-/var/lib/nginx-ui/plugins/public-ip-inventory}"

python3 "${ROOT_DIR}/bin/public-ip-inventory-server" --backup
