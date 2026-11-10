#!/bin/sh
# Sauvegarde des bases xpass et keycloak (format personnalisé pg_dump, compressé), conservée 14 jours.
# Restauration : pg_restore --clean --if-exists -d xpass /backups/xpass-AAAAMMJJ-HHMM.dump
set -eu
stamp=$(date -u +%Y%m%d-%H%M)
for db in xpass keycloak; do
  pg_dump -Fc -d "$db" -f "/backups/$db-$stamp.dump.tmp"
  mv "/backups/$db-$stamp.dump.tmp" "/backups/$db-$stamp.dump"
done
find /backups -name '*.dump' -mtime +14 -delete
echo "sauvegarde $stamp terminée"
