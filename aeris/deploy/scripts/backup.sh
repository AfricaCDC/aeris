#!/usr/bin/env bash
# AERIS daily database backup. Run from the deploy folder, e.g. cron at 02:30:
#   30 2 * * *  cd /opt/aeris/deploy && ./scripts/backup.sh >> /var/log/aeris-backup.log 2>&1
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a

BACKUP_DIR="${BACKUP_DIR:-/var/backups/aeris}"
KEEP="${BACKUP_KEEP_DAYS:-30}"
STAMP="$(date -u +%Y%m%d-%H%M%S)"
FILE="${BACKUP_DIR}/aeris-${STAMP}.sql.gz"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

# Consistent dump without locking AERIS (InnoDB)
docker compose -f docker-compose.prod.yml exec -T db sh -c \
  'exec mariadb-dump --single-transaction --routines --triggers --default-character-set=utf8 -uroot -p"$MARIADB_ROOT_PASSWORD" openboxes' \
  | gzip -9 > "${FILE}.part"
mv "${FILE}.part" "$FILE"

# Refuse a suspiciously small dump (empty or failed)
SIZE=$(stat -c %s "$FILE")
if [ "$SIZE" -lt 100000 ]; then
  echo "$(date -u) ERROR backup $FILE is only $SIZE bytes" >&2
  exit 1
fi
sha256sum "$FILE" > "${FILE}.sha256"
echo "$(date -u) OK $FILE ($SIZE bytes)"

# Keep the last N days
find "$BACKUP_DIR" -name 'aeris-*.sql.gz*' -mtime +"$KEEP" -delete

# Optional copy off the server (a backup on the same disk does not survive the server)
if [ -n "${BACKUP_OFFSITE_CMD:-}" ]; then
  eval "${BACKUP_OFFSITE_CMD//\{file\}/$FILE}"
  eval "${BACKUP_OFFSITE_CMD//\{file\}/$FILE.sha256}"
  echo "$(date -u) copied off-site"
fi
