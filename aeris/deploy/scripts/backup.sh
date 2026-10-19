#!/usr/bin/env bash
# AERIS daily database backup. Run from the deploy folder, e.g. cron at 02:30:
#   30 2 * * *  cd /opt/aeris/deploy && ./scripts/backup.sh >> /var/log/aeris-backup.log 2>&1
set -euo pipefail
cd "$(dirname "$0")/.."

# Read only the settings this script needs (.env uses Docker's format: unquoted values may contain spaces)
env_get() { grep -E "^$1=" .env | tail -1 | cut -d= -f2- | sed -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'\$/\1/"; }
BACKUP_DIR="$(env_get BACKUP_DIR)"
BACKUP_KEEP_DAYS="$(env_get BACKUP_KEEP_DAYS)"
BACKUP_OFFSITE_CMD="$(env_get BACKUP_OFFSITE_CMD)"

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

# Refuse an empty or failed dump (the schema alone compresses to about 80 KB)
SIZE=$(stat -c %s "$FILE")
if [ "$SIZE" -lt 20000 ]; then
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
