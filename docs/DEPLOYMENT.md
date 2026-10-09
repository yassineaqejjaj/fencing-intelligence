# Deployment

This is a self-hosted deployment. It has not been exercised as a public production launch in this repository. The Compose files and the production startup checks are the verified configuration surface.

## Local

`docker compose up -d postgres redis minio` starts PostgreSQL 16, Redis 7, and the pinned Silo S3-compatible server. Build and start the API, worker, and web only after the Dockerfiles in `infrastructure/docker` are present:

```bash
docker compose up -d --build api worker web
```

If 8000 or 3000 is already in use, set `API_PORT` and `WEB_PORT` first. Postgres, Redis, and object storage keep their own ports.

The API container runs `alembic upgrade head` before Uvicorn. The worker container runs Dramatiq. `INLINE_JOBS` is false.

## Production Compose

`docker-compose.prod.yml` keeps databases off the public ports, sets resource limits, and expects secrets from the environment. Before starting it:

1. Set `ENVIRONMENT=production`.
2. Set `SECRET_KEY` to a unique value of at least 32 characters.
3. Set object-storage credentials that are not the development pair.
4. Set `COOKIE_SECURE=true`.
5. Terminate TLS in front of the web service. A Caddy example is in `infrastructure/deployment/Caddyfile`. Point the site at the web container and proxy `/api/v1` to the API if you are not using the Next.js rewrite.
6. Set `TRUST_PROXY=true` only when that proxy is the only path to the API.
7. Keep `INLINE_JOBS=false` and run the worker.
8. Configure SMTP (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_STARTTLS`). Without it, password resets cannot be delivered (the API logs `password_reset_email_unsent` and keeps a generic response) and invitations return their token to the inviting administrator instead.
9. Restrict `CORS_ORIGINS` to the public web origin.

The API refuses to start in production when those secret checks fail.

## Retention

Run the purge on a schedule (systemd timer or cron on the API host):

```bash
docker compose -f docker-compose.prod.yml exec api python -m fencing_api.retention --days 30
docker compose -f docker-compose.prod.yml exec api python -m fencing_api.retention --days 30 --apply
```

Always dry-run first. Expire backup sets on the same schedule; see `docs/BACKUP.md`.

## Monitoring

Point Prometheus at the API `/metrics` (example in `infrastructure/monitoring/prometheus.yml`, alerts in `alerts.yml`: API down, 5xx rate, p95 latency, video-endpoint failures). Watch worker queue depth and disk usage alongside.

## Health

- `GET /health` returns process liveness.
- `GET /ready` checks Postgres, Redis, and the bucket.
- `GET /metrics` exposes Prometheus metrics.

## Migrations

Apply Alembic migrations before serving traffic. The API image does this on start. Take a backup first. See `docs/BACKUP.md`.

## GPU

No service requires a GPU. Optional ML packages are extras and are not installed by the API image.
