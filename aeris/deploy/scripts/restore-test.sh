#!/usr/bin/env bash
# AERIS monthly restore test: loads a backup into a throwaway database next to production
# and checks that the key tables are there. Production data is not touched.
#   ./scripts/restore-test.sh [/var/backups/aeris/aeris-YYYYMMDD-HHMMSS.sql.gz]   (default: latest)
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a

FILE="${1:-$(ls -1t "${BACKUP_DIR:-/var/backups/aeris}"/aeris-*.sql.gz | head -1)}"
[ -f "$FILE" ] || { echo "No backup found"; exit 1; }
if [ -f "${FILE}.sha256" ]; then sha256sum -c "${FILE}.sha256"; fi

DC="docker compose -f docker-compose.prod.yml"
DB=openboxes_restore_test
echo "Restoring $FILE into $DB ..."
$DC exec -T db sh -c "mariadb -uroot -p\"\$MARIADB_ROOT_PASSWORD\" -e 'DROP DATABASE IF EXISTS $DB; CREATE DATABASE $DB DEFAULT CHARACTER SET utf8'"
gunzip -c "$FILE" | $DC exec -T db sh -c "exec mariadb -uroot -p\"\$MARIADB_ROOT_PASSWORD\" $DB"

echo "Row counts in the restored copy:"
$DC exec -T db sh -c "mariadb -uroot -p\"\$MARIADB_ROOT_PASSWORD\" -N $DB -e \"
  select 'products', count(*) from product union all
  select 'locations', count(*) from location union all
  select 'users', count(*) from user union all
  select 'transactions', count(*) from transaction union all
  select 'last transaction', max(transaction_date) from transaction\""

$DC exec -T db sh -c "mariadb -uroot -p\"\$MARIADB_ROOT_PASSWORD\" -e 'DROP DATABASE $DB'"
echo "$(date -u) restore test OK for $FILE"
