#!/bin/bash
# Daily PostgreSQL backup script
# Usage: ./backup.sh
# Add to crontab: 0 2 * * * /path/to/backup.sh

BACKUP_DIR="/backups/postgres"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_NAME="orchagent"
DB_USER="orchagent"
DB_PASSWORD="orchagent"

mkdir -p "$BACKUP_DIR"

PGPASSWORD="$DB_PASSWORD" pg_dump -U "$DB_USER" -h localhost "$DB_NAME" | gzip > "$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql.gz"

find "$BACKUP_DIR" -name "${DB_NAME}_*.sql.gz" -mtime +30 -delete

echo "Backup completed: ${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.sql.gz"
