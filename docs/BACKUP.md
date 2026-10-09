# Backup and restore

Back up PostgreSQL and the object-storage bucket together. A database backup without the video objects cannot play video. An object backup without the database cannot authorize playback.

## Scripts (tested drill, 2026-10-08)

`scripts/backup.sh` writes a timestamped `fencing-<stamp>.dump` plus an incremental `bucket-<stamp>/` mirror of the video bytes (via `scripts/s3_mirror.py`, needs `boto3`). `scripts/restore.sh` loads the dump and mirrors the bytes back; restore never deletes remote keys, so it cannot wipe newer video.

```bash
# Dev defaults (override S3_*/POSTGRES_*/COMPOSE_FILE for other stacks):
PYTHON=/path/to/venv/bin/python S3_BUCKET=fencing-videos ./scripts/backup.sh /srv/backups/fi
./scripts/restore.sh /srv/backups/fi/fencing-20261008T214054Z.dump
```

Environment honored by both scripts: `COMPOSE_FILE`, `POSTGRES_USER`, `POSTGRES_DB`, `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET`, `S3_REGION`, `PYTHON` (interpreter with boto3), `SKIP_BUCKET_MIRROR=1` (database only, loudly reported).

Stop the API and worker before restoring so they do not write during the load. Run `alembic upgrade head` afterward if the dump is older than the code.

Signed URLs are not backups. They expire.

## Retention interplay

Backups keep whatever they copied, including videos a user later deletes. If your policy promises erasure after N days, expire backup sets on the same schedule (or shorter): the `retention_purge` job removes live data, not backup copies. Document the backup lifetime next to the retention policy.

## Manual equivalent

Database:

```bash
docker compose exec -T postgres pg_dump -U fencing -d fencing --format=custom > fencing.dump
```

Restore into the same database:

```bash
docker compose exec -T postgres pg_restore -U fencing -d fencing --clean --if-exists < fencing.dump
```

## Objects

Use an S3 client against the same endpoint, bucket, and credentials as the API. Mirror the bucket to another bucket or disk. Restore by mirroring back before you start the API.

## What not to copy

Do not put dumps in git. They contain accounts, annotations, and references to private video. Store them where the same access rules as the application apply.
