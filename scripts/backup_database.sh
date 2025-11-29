#!/bin/bash
# Database Backup Script for Prep Application
#
# This script creates automated backups of the PostgreSQL database
# with support for both local and cloud storage (S3/MinIO).
#
# Usage:
#   ./scripts/backup_database.sh [options]
#
# Options:
#   --full          Create a full backup (default)
#   --incremental   Create an incremental backup using WAL archiving
#   --restore FILE  Restore from a backup file
#   --list          List available backups
#   --cleanup DAYS  Remove backups older than DAYS days
#   --upload        Upload backup to S3/MinIO
#
# Environment Variables:
#   DATABASE_URL    - PostgreSQL connection string (required)
#   BACKUP_DIR      - Local backup directory (default: ./backups)
#   S3_BUCKET       - S3/MinIO bucket for remote storage
#   S3_ENDPOINT     - S3/MinIO endpoint URL
#   AWS_ACCESS_KEY_ID     - S3 access key
#   AWS_SECRET_ACCESS_KEY - S3 secret key
#
# Examples:
#   ./scripts/backup_database.sh --full --upload
#   ./scripts/backup_database.sh --cleanup 30
#   ./scripts/backup_database.sh --restore backups/backup_2025-11-28.sql.gz

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Check required tools
check_dependencies() {
    local missing_deps=()

    if ! command -v pg_dump &> /dev/null; then
        missing_deps+=("pg_dump")
    fi

    if ! command -v gzip &> /dev/null; then
        missing_deps+=("gzip")
    fi

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing dependencies: ${missing_deps[*]}"
        log_error "Install PostgreSQL client tools: brew install postgresql (macOS) or apt-get install postgresql-client (Linux)"
        exit 1
    fi
}

# Parse DATABASE_URL into components
parse_database_url() {
    if [[ -z "${DATABASE_URL:-}" ]]; then
        log_error "DATABASE_URL environment variable is not set"
        exit 1
    fi

    # Parse postgresql://user:password@host:port/dbname
    local url="${DATABASE_URL#postgresql://}"
    url="${url#postgres://}"

    # Handle asyncpg URLs
    url="${url#postgresql+asyncpg://}"

    # Extract user:password
    local userpass="${url%%@*}"
    PGUSER="${userpass%%:*}"
    PGPASSWORD="${userpass#*:}"

    # Extract host:port/dbname
    local hostpart="${url#*@}"
    local hostport="${hostpart%%/*}"
    PGHOST="${hostport%%:*}"
    PGPORT="${hostport#*:}"
    PGPORT="${PGPORT:-5432}"

    # Extract database name (remove query params)
    PGDATABASE="${hostpart#*/}"
    PGDATABASE="${PGDATABASE%%\?*}"

    export PGHOST PGPORT PGUSER PGPASSWORD PGDATABASE
}

# Create backup directory
ensure_backup_dir() {
    if [[ ! -d "$BACKUP_DIR" ]]; then
        log_info "Creating backup directory: $BACKUP_DIR"
        mkdir -p "$BACKUP_DIR"
    fi
}

# Full backup
create_full_backup() {
    local backup_file="$BACKUP_DIR/backup_${TIMESTAMP}_full.sql.gz"

    log_info "Starting full backup of database: $PGDATABASE"
    log_info "Backup file: $backup_file"

    # Create backup with progress
    pg_dump \
        --verbose \
        --format=plain \
        --no-owner \
        --no-privileges \
        --if-exists \
        --clean \
        "$PGDATABASE" 2>&1 | gzip > "$backup_file"

    local size=$(du -h "$backup_file" | cut -f1)
    log_info "Backup completed successfully. Size: $size"

    # Create a checksum
    if command -v sha256sum &> /dev/null; then
        sha256sum "$backup_file" > "$backup_file.sha256"
        log_info "Checksum created: $backup_file.sha256"
    elif command -v shasum &> /dev/null; then
        shasum -a 256 "$backup_file" > "$backup_file.sha256"
        log_info "Checksum created: $backup_file.sha256"
    fi

    # Create metadata file
    cat > "$backup_file.meta" << EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "database": "$PGDATABASE",
    "host": "$PGHOST",
    "type": "full",
    "size_bytes": $(stat -f%z "$backup_file" 2>/dev/null || stat -c%s "$backup_file"),
    "pg_version": "$(pg_dump --version | head -1)"
}
EOF

    echo "$backup_file"
}

# Schema-only backup (for migrations/structure)
create_schema_backup() {
    local backup_file="$BACKUP_DIR/schema_${TIMESTAMP}.sql"

    log_info "Creating schema-only backup..."

    pg_dump \
        --schema-only \
        --no-owner \
        --no-privileges \
        "$PGDATABASE" > "$backup_file"

    log_info "Schema backup created: $backup_file"
    echo "$backup_file"
}

# Restore from backup
restore_backup() {
    local backup_file="$1"

    if [[ ! -f "$backup_file" ]]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi

    log_warn "WARNING: This will overwrite the current database: $PGDATABASE"
    read -p "Are you sure you want to continue? (yes/no): " confirm

    if [[ "$confirm" != "yes" ]]; then
        log_info "Restore cancelled"
        exit 0
    fi

    log_info "Restoring database from: $backup_file"

    if [[ "$backup_file" == *.gz ]]; then
        gunzip -c "$backup_file" | psql "$PGDATABASE"
    else
        psql "$PGDATABASE" < "$backup_file"
    fi

    log_info "Restore completed successfully"
}

# List available backups
list_backups() {
    log_info "Available backups in $BACKUP_DIR:"
    echo ""

    if [[ -d "$BACKUP_DIR" ]]; then
        ls -lh "$BACKUP_DIR"/*.sql.gz 2>/dev/null || log_info "No backups found"
    else
        log_info "Backup directory does not exist"
    fi
}

# Cleanup old backups
cleanup_old_backups() {
    local days="${1:-$BACKUP_RETENTION_DAYS}"

    log_info "Removing backups older than $days days..."

    if [[ -d "$BACKUP_DIR" ]]; then
        local count=$(find "$BACKUP_DIR" -name "*.sql.gz" -mtime +"$days" | wc -l | tr -d ' ')

        if [[ "$count" -gt 0 ]]; then
            find "$BACKUP_DIR" -name "*.sql.gz" -mtime +"$days" -delete
            find "$BACKUP_DIR" -name "*.sha256" -mtime +"$days" -delete
            find "$BACKUP_DIR" -name "*.meta" -mtime +"$days" -delete
            log_info "Removed $count old backup(s)"
        else
            log_info "No old backups to remove"
        fi
    fi
}

# Upload to S3/MinIO
upload_to_s3() {
    local backup_file="$1"

    if [[ -z "${S3_BUCKET:-}" ]]; then
        log_warn "S3_BUCKET not set, skipping upload"
        return 0
    fi

    if ! command -v aws &> /dev/null; then
        log_warn "AWS CLI not installed, skipping upload"
        log_info "Install with: pip install awscli"
        return 0
    fi

    local s3_path="s3://$S3_BUCKET/database-backups/$(basename "$backup_file")"

    log_info "Uploading to: $s3_path"

    local aws_opts=()
    if [[ -n "${S3_ENDPOINT:-}" ]]; then
        aws_opts+=(--endpoint-url "$S3_ENDPOINT")
    fi

    aws "${aws_opts[@]}" s3 cp "$backup_file" "$s3_path"

    # Also upload metadata
    if [[ -f "$backup_file.meta" ]]; then
        aws "${aws_opts[@]}" s3 cp "$backup_file.meta" "$s3_path.meta"
    fi
    if [[ -f "$backup_file.sha256" ]]; then
        aws "${aws_opts[@]}" s3 cp "$backup_file.sha256" "$s3_path.sha256"
    fi

    log_info "Upload completed"
}

# Verify backup integrity
verify_backup() {
    local backup_file="$1"

    if [[ ! -f "$backup_file" ]]; then
        log_error "Backup file not found: $backup_file"
        return 1
    fi

    log_info "Verifying backup integrity..."

    # Check if file can be decompressed
    if [[ "$backup_file" == *.gz ]]; then
        if ! gzip -t "$backup_file" 2>/dev/null; then
            log_error "Backup file is corrupted (gzip test failed)"
            return 1
        fi
    fi

    # Verify checksum if available
    if [[ -f "$backup_file.sha256" ]]; then
        if command -v sha256sum &> /dev/null; then
            if sha256sum -c "$backup_file.sha256" &>/dev/null; then
                log_info "Checksum verification passed"
            else
                log_error "Checksum verification failed"
                return 1
            fi
        elif command -v shasum &> /dev/null; then
            if shasum -a 256 -c "$backup_file.sha256" &>/dev/null; then
                log_info "Checksum verification passed"
            else
                log_error "Checksum verification failed"
                return 1
            fi
        fi
    fi

    log_info "Backup verification completed successfully"
    return 0
}

# Main function
main() {
    local action="full"
    local upload=false
    local restore_file=""
    local cleanup_days=""
    local verify_file=""

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --full)
                action="full"
                shift
                ;;
            --schema)
                action="schema"
                shift
                ;;
            --restore)
                action="restore"
                restore_file="$2"
                shift 2
                ;;
            --list)
                action="list"
                shift
                ;;
            --cleanup)
                action="cleanup"
                cleanup_days="${2:-$BACKUP_RETENTION_DAYS}"
                shift
                [[ "${1:-}" =~ ^[0-9]+$ ]] && shift
                ;;
            --upload)
                upload=true
                shift
                ;;
            --verify)
                action="verify"
                verify_file="$2"
                shift 2
                ;;
            --help|-h)
                echo "Database Backup Script for Prep Application"
                echo ""
                echo "Usage: $0 [options]"
                echo ""
                echo "Options:"
                echo "  --full          Create a full backup (default)"
                echo "  --schema        Create a schema-only backup"
                echo "  --restore FILE  Restore from a backup file"
                echo "  --list          List available backups"
                echo "  --cleanup DAYS  Remove backups older than DAYS days"
                echo "  --upload        Upload backup to S3/MinIO"
                echo "  --verify FILE   Verify backup integrity"
                echo "  --help          Show this help message"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Check dependencies
    check_dependencies

    # Execute action
    case $action in
        full)
            parse_database_url
            ensure_backup_dir
            backup_file=$(create_full_backup)
            if $upload; then
                upload_to_s3 "$backup_file"
            fi
            ;;
        schema)
            parse_database_url
            ensure_backup_dir
            create_schema_backup
            ;;
        restore)
            parse_database_url
            restore_backup "$restore_file"
            ;;
        list)
            list_backups
            ;;
        cleanup)
            cleanup_old_backups "$cleanup_days"
            ;;
        verify)
            verify_backup "$verify_file"
            ;;
    esac
}

main "$@"
