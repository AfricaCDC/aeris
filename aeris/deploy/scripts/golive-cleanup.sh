#!/usr/bin/env bash
# AERIS go-live clean-up of OpenBoxes demo leftovers. Safe to run more than once.
#  - "Main Warehouse" (OpenBoxes' built-in demo depot): deactivated, if it holds no stock
#  - the seed admin "Miss Administrator": renamed "AERIS Administrator" (shown as "Handled by" on documents)
#   ./scripts/golive-cleanup.sh
set -euo pipefail
cd "$(dirname "$0")/.."

docker compose -f docker-compose.prod.yml exec -T db sh -c 'exec mariadb --default-character-set=utf8 -uroot -p"$MARIADB_ROOT_PASSWORD" openboxes' <<'SQL'
UPDATE location l
   SET l.active = 0, l.last_updated = NOW()
 WHERE l.name = 'Main Warehouse'
   AND (l.active IS NULL OR l.active = 1)
   AND NOT EXISTS (SELECT 1 FROM product_availability pa WHERE pa.location_id = l.id AND pa.quantity_on_hand <> 0);
SELECT CONCAT('Main Warehouse deactivated: ', ROW_COUNT()) AS result;

UPDATE person p JOIN user u ON u.id = p.id
   SET p.first_name = 'AERIS', p.last_name = 'Administrator', p.last_updated = NOW()
 WHERE u.username = 'admin' AND p.first_name = 'Miss' AND p.last_name = 'Administrator';
SELECT CONCAT('Seed admin renamed: ', ROW_COUNT()) AS result;
SQL
echo "Done. Restart not needed; users see the change at their next sign-in."
