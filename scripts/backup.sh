#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
stamp=$(date -u +%Y%m%dT%H%M%SZ)
out=${1:-"$root/backups"}
mkdir -p "$out"
compose_file="${COMPOSE_FILE:-$root/docker-compose.yml}"
pg_user="${POSTGRES_USER:-fencing}"
pg_db="${POSTGRES_DB:-fencing}"
docker compose -f "$compose_file" exec -T postgres pg_dump -U "$pg_user" -d "$pg_db" --format=custom > "$out/fencing-$stamp.dump"
echo "Wrote $out/fencing-$stamp.dump"
if [ "${SKIP_BUCKET_MIRROR:-0}" = "1" ]; then
  echo "SKIP_BUCKET_MIRROR=1: bucket bytes were NOT mirrored."
  exit 0
fi
if ! "${PYTHON:-python3}" -c "import boto3" 2>/dev/null; then
  echo "boto3 is required to mirror video bytes (pip install boto3), or set SKIP_BUCKET_MIRROR=1." >&2
  exit 1
fi
S3_ENDPOINT_URL="${S3_ENDPOINT_URL:-http://localhost:9000}" \
S3_ACCESS_KEY="${S3_ACCESS_KEY:-fencing}" \
S3_SECRET_KEY="${S3_SECRET_KEY:-fencingsecret}" \
S3_BUCKET="${S3_BUCKET:-fencing-videos}" \
S3_REGION="${S3_REGION:-us-east-1}" \
"${PYTHON:-python3}" "$root/scripts/s3_mirror.py" backup "$out/bucket-$stamp"
