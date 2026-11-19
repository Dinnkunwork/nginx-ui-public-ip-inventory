#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="${ROOT_DIR}/dist"
PLUGIN_ID="com.company.public-ip-inventory"
VERSION="1.0.0"
PACKAGE_NAME="${PLUGIN_ID}-${VERSION}.tar.gz"

echo "Building frontend bundle..."
if [[ -d "${ROOT_DIR}/webapp/node_modules" ]]; then
  npm --prefix "${ROOT_DIR}/webapp" run build
else
  echo "Warning: webapp/node_modules not found. Run 'npm --prefix webapp install && npm --prefix webapp run build' first if packaging for production."
fi

echo "Running backend tests..."
python3 -m unittest discover -s "${ROOT_DIR}/tests" -v

mkdir -p "${DIST_DIR}"
STAGE_DIR="$(mktemp -d)"
trap 'rm -rf "${STAGE_DIR}"' EXIT

mkdir -p "${STAGE_DIR}/bin" "${STAGE_DIR}/server" "${STAGE_DIR}/webapp"
cp "${ROOT_DIR}/plugin.json" "${STAGE_DIR}/"
cp "${ROOT_DIR}/bin/public-ip-inventory-server" "${STAGE_DIR}/bin/"
chmod 0755 "${STAGE_DIR}/bin/public-ip-inventory-server"
cp "${ROOT_DIR}/server/"*.py "${STAGE_DIR}/server/"

if [[ -d "${ROOT_DIR}/webapp/dist" ]]; then
  cp -r "${ROOT_DIR}/webapp/dist" "${STAGE_DIR}/webapp/dist"
fi

TAR_ITEMS=("plugin.json" "bin" "server")
if [[ -d "${STAGE_DIR}/webapp/dist" ]]; then
  TAR_ITEMS+=("webapp")
fi

tar -czf "${DIST_DIR}/${PACKAGE_NAME}" -C "${STAGE_DIR}" "${TAR_ITEMS[@]}"
echo "Created plugin package: ${DIST_DIR}/${PACKAGE_NAME}"
