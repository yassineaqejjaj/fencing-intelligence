#!/bin/sh
set -eu
if [ $# -lt 1 ] || [ $# -gt 2 ]; then
  echo "usage: scripts/restore.sh path/to/fencing.dump [path/to/bucket-dir]" >&2
  exit 1
fi
root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
dump=$1
bucket_dir=${2:-$(dirname "$dump")/$(basename "$dump" | sed 's/^fencing-/bucket-/; s/\.dump$//')}
echo "Stop the API and worker before restoring."
compose_file="${COMPOSE_FILE:-$root/docker-compose.yml}"
pg_user="${POSTGRES_USER:-fencing}"
pg_db="${POSTGRES_DB:-fencing}"
docker compose -f "$compose_file" exec -T postgres pg_restore -U "$pg_user" -d "$pg_db" --clean --if-exists < "$dump"
if [ -d "$bucket_dir" ]; then
  if ! "${PYTHON:-python3}" -c "import boto3" 2>/dev/null; then
    echo "boto3 is required to restore video bytes (pip install boto3)." >&2
    exit 1
  fi
  S3_ENDPOINT_URL="${S3_ENDPOINT_URL:-http://localhost:9000}" \
  S3_ACCESS_KEY="${S3_ACCESS_KEY:-fencing}" \
  S3_SECRET_KEY="${S3_SECRET_KEY:-fencingsecret}" \
  S3_BUCKET="${S3_BUCKET:-fencing-videos}" \
  S3_REGION="${S3_REGION:-us-east-1}" \
  "${PYTHON:-python3}" "$root/scripts/s3_mirror.py" restore "$bucket_dir"
else
  echo "No bucket mirror at $bucket_dir: database restored, video bytes untouched."
fi
echo "Run alembic upgrade head before serving traffic."
