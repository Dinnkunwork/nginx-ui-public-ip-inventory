# Installation Guide (Ubuntu Linux + Nginx UI v3.0.0)

## Prerequisites

- Ubuntu Linux with **Nginx UI v3.0.0+**
- `python3` (3.10+ recommended; pre-installed on Ubuntu)
- Node.js 20+ & npm (only required on the build machine to compile `webapp/dist`)

## 1. Build the Frontend & Package

On a machine with network access:

```bash
npm --prefix webapp install
./scripts/package.sh
```

This produces `dist/com.company.public-ip-inventory-1.0.0.tar.gz`.

## 2. Install into Nginx UI v3.0.0

Choose one of the official Nginx UI v3.0.0 installation methods:

### Option A: CLI

```bash
sudo nginx-ui plugin install dist/com.company.public-ip-inventory-1.0.0.tar.gz
```

### Option B: Web UI

1. Open **System > Plugins** in Nginx UI.
2. Upload `dist/com.company.public-ip-inventory-1.0.0.tar.gz`.
3. Review permissions (none requested) and enable the plugin.

### Option C: Offline Directory

Copy the `.tar.gz` into `<nginx-ui-config-dir>/plugins/packages/` and restart Nginx UI.

## 3. Database Directory Permissions

If using the default standalone path `/var/lib/nginx-ui/plugins/public-ip-inventory`:

```bash
sudo mkdir -p /var/lib/nginx-ui/plugins/public-ip-inventory/backups
sudo chown -R root:root /var/lib/nginx-ui/plugins/public-ip-inventory
sudo chmod 0700 /var/lib/nginx-ui/plugins/public-ip-inventory
```

## 4. Verification

1. Reload Nginx UI in your browser.
2. Verify **Public IP Inventory** appears in the sidebar with **Dashboard**, **IP Address List**, **Add IP Address**, and **Reports**.
3. Add a test IP, verify it appears in the table and dashboard counts, and delete it with confirmation.
