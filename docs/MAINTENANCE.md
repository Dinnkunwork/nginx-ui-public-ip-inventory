# Maintenance, Backup & Recovery

## Online SQLite Backups

The plugin uses Python's `sqlite3.Connection.backup()` API, which safely snapshots the active WAL database without stopping Nginx UI.

### Via Web UI

1. Go to **Public IP Inventory > Reports**.
2. Click **Create Backup Now** under **SQLite Database Backups**.

### Via CLI / Cron

Run the included backup script (e.g. daily at 02:00 via cron):

```bash
0 2 * * * /path/to/ip-inventory/scripts/backup-db.sh >> /var/log/public-ip-inventory-backup.log 2>&1
```

Backups are stored in `<backup_dir>/public-ip-inventory-YYYYMMDD-HHMMSS.db` with `0600` permissions.

## Restore Procedure

1. Go to **Public IP Inventory > Reports**.
2. Locate the desired backup in **SQLite Database Backups** and click **Restore**.
3. Confirm the prompt. The backend automatically creates a `pre-restore` safety backup before restoring.

## Pre-Upgrade Checklist

Before upgrading the plugin or Nginx UI:

1. Create a manual backup via **Reports > Create Backup Now** or `scripts/backup-db.sh`.
2. Verify the backup file exists and is non-empty.
3. Upgrade the plugin or Nginx UI and restart the service.
4. Verify **Public IP Inventory > Dashboard** displays the expected counts.
