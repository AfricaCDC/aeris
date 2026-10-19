#!/usr/bin/env bash
# AERIS monthly restore test: loads a backup into a throwaway database next to production
# and checks that the key tables are there. Production data is not touched.
#   ./scripts/restore-test.sh [/var/backups/aeris/aeris-YYYYMMDD-HHMMSS.sql.gz]   (default: latest)
set -euo pipefail
cd "$(dirname "$0")/.."

# Read only the settings this script needs (.env uses Docker's format: unquoted values may contain spaces)
env_get() { grep -E "^$1=" .env | tail -1 | cut -d= -f2- | sed -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'\$/\1/"; }
BACKUP_DIR="$(env_get BACKUP_DIR)"

FILE="${1:-$(ls -1t "${BACKUP_DIR:-/var/backups/aeris}"/aeris-*.sql.gz | head -1)}"
[ -f "$FILE" ] || { echo "No backup found"; exit 1; }
if [ -f "${FILE}.sha256" ]; then
  ( cd "$(dirname "$FILE")" && sha256sum -c "$(basename "$FILE").sha256" )
fi

DC="docker compose -f docker-compose.prod.yml"
DB=openboxes_restore_test
echo "Restoring $FILE into $DB ..."
$DC exec -T db sh -c "mariadb -uroot -p\"\$MARIADB_ROOT_PASSWORD\" -e 'DROP DATABASE IF EXISTS $DB; CREATE DATABASE $DB DEFAULT CHARACTER SET utf8'"
# The views in the dump belong to the application user, who has no rights on the test database:
# drop the DEFINER clauses so they run as the restoring user (a real restore into 'openboxes' keeps them).
gunzip -c "$FILE" \
  | sed -e 's#/\*!50013 DEFINER=[^*]*\*/##g' -e 's#/\*!50017 DEFINER=[^*]*\*/##g' -e 's#DEFINER=`[^`]*`@`[^`]*`##g' \
  | $DC exec -T db sh -c "exec mariadb -uroot -p\"\$MARIADB_ROOT_PASSWORD\" $DB"

echo "Row counts in the restored copy:"
$DC exec -T db sh -c "mariadb -uroot -p\"\$MARIADB_ROOT_PASSWORD\" -N $DB -e \"
  select 'products', count(*) from product union all
  select 'locations', count(*) from location union all
  select 'users', count(*) from user union all
  select 'transactions', count(*) from transaction union all
  select 'last transaction', max(transaction_date) from transaction\""

$DC exec -T db sh -c "mariadb -uroot -p\"\$MARIADB_ROOT_PASSWORD\" -e 'DROP DATABASE $DB'"
echo "$(date -u) restore test OK for $FILE"
