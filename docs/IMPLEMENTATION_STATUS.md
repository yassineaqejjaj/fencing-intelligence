# Implementation status

Checked on 8 October 2026 against this working tree. A feature is listed as tested only when a command in this session finished successfully.

## Verified commands

- `services/api`: `pytest tests ../../packages/fencing-domain/tests -q` passed. One test was skipped because scikit-learn is not installed. The suite uses Postgres, Redis, and the S3-compatible server. The video case transcodes a generated clip with FFmpeg.
- `datasets doctor --root data/datasets` ran. Installed datasets: 0. Missing: 5. Incompatible: 5. The rules taxonomy is a reference. Athlete uploads are a product feature and restricted.
- `apps/web`: `tsc --noEmit` passed. `vitest run` passed (2 tests).
- Playwright `e2e/journey.spec.ts` passed against the running web app on port 3001 and the API on port 8001. The browser registered an account, created a club and two athletes, created a dated bout, uploaded a generated MP4, waited until processing reported ready, saved a validated annotation, recorded a touch, opened performance statistics, generated a PDF report, opened datasets, models, coach, training, and privacy, then confirmed a second organization cannot open the first video.
- `GET /health` and `GET /ready` on the local API returned ready for database, Redis, and object storage.

Ports 8000 and 3000 were already taken by another Docker process on this machine. The fencing API and web app were started on 8001 and 3001. The documented defaults remain 8000 and 3000.

## Workarounds added on 8 October 2026

- `FI-synthetic-epee` is original Apache-2.0 data bundled with the app. `datasets doctor` reports it installed. MFAD, FFD, fencing-AI, FencingVision, and the GPL-3.0 FIE repository are still not downloaded or copied.
- Pose estimation uses the Apache-2.0 MediaPipe pose landmarker. It stores joint positions and does not name fencing actions. OpenCV frame sampling is installed for scoreboard checks.
- A logistic-regression baseline was fit on separated synthetic clusters. Its holdout score is a pipeline check, not fencing accuracy.
- Coaching text is assembled from stored statistics. No language model is called.
- The analysis page can mark a phrase, open annotation history, and save a piste calibration. Distance stays in pixels until that calibration exists.
- `apps/web/src/lib/api-schema.ts` is generated from the API OpenAPI document.
- `docker compose build` produced the API and web images. They were started on ports 8002 and 3002 because 8000 and 3000 were already taken. `GET /health`, `GET /ready`, and the web home page responded successfully.
- Object storage still uses the pinned Silo image. Any other S3 endpoint can be set with `S3_ENDPOINT_URL`.

## Not verified here

- GitHub Actions has not run on a GitHub-hosted runner.
- No model in this repository has been evaluated on real fencing video. No recognition accuracy is claimed.
- No load test: concurrent uploads and transcode queue depth under pressure are unmeasured. The worker runs one process with two threads by default.
- `pnpm audit` found 1 high advisory in `braces` (build-time only, via `eslint-config-next`; no patched release published yet). `pip-audit` is clean.

## Production readiness pass (8 October 2026, evening)

- `docker-compose.prod.yml` booted as a staging stack with generated secrets (`ENVIRONMENT=production`, 64-hex `SECRET_KEY`, non-default S3 credentials, `COOKIE_SECURE=true`, `INLINE_JOBS=false`). Migrations ran automatically on API start, `/health` and `/ready` report ready, and the full flow passed through the web proxy: register, athletes, bout, multipart upload, worker transcode to `ready`, annotation, validation, touch, statistics, invitation. Findings fixed: missing `.dockerignore` (1.2 GB build context that included `.env`), success notices on the competition page never rendered (cleared synchronously by refresh), and the login page advertised local demo credentials on production builds (now gated on `NODE_ENV !== "production"`).
- Compose port mappings merge across override files, so staging used a manually recreated web container on 127.0.0.1:3101 instead of the file's 127.0.0.1:3000 (taken on this machine). The MinIO/S3 public endpoint was published as 127.0.0.1:9100 for the same reason.
- `scripts/backup.sh` / `scripts/restore.sh` now cover video bytes via `scripts/s3_mirror.py` (boto3, incremental, restore never deletes). Drill on the dev stack: pg_dump, witness row inserted, pg_restore removed the witness, one deleted bucket key re-mirrored back (1 file, 2072 bytes).
- Mailer: `send_email` returns delivered/dropped, logs `email_dropped_no_smtp` and `password_reset_email_unsent`, supports `SMTP_STARTTLS=false` relays, and invitations return `email_sent` plus the token to the inviting administrator when SMTP is absent.
- Guardian consent for minors (migration `7d3e9c1a5f42`): `consent_records.athlete_id` + `details`, `POST /athletes/{id}/guardian-consent` (latest record wins), `is_minor`/`guardian_consent_granted` on athlete payloads, uploads of minor video without consent are forced private (`visibility_forced_private`) and `training_consent` is refused with `guardian_consent_required`. `python -m fencing_api.retention --days 30 [--apply]` hard-purges soft-deleted videos (keys + rows; audit log kept). UI: minor badge + consent card on the athlete page, forced-private notice on the video page.
- Hardening: per-user upload rate limit (`UPLOAD_RATE_LIMIT`, 20/hour default), Caddy HSTS + hardening headers, `SECURITY.md` updated.
- Observability: `infrastructure/monitoring/alerts.yml` (ApiDown, ApiErrors, ApiSlow, UploadFailures, matched against live `status="Nxx"` label values) wired into `prometheus.yml`.
- Tests: API suite 27 passed (guardian consent 4, rate limit 1, federation 6, rest unchanged); `tsc` clean; `vitest` 2 passed; Playwright journey + new `federation.spec.ts` (minor athlete, guardian grant, entries, poules, standings, DE) green.
- OpenAPI regenerated (75 paths) into `apps/web/src/lib/openapi.json` + `api-schema.ts`.

## Product state

The manual path works: account, club, athlete, bout, upload, playback, annotation, touch, statistics, report, export endpoints, and organization isolation. Statistics stay empty until a person validates an annotation or a touch. Charts are not drawn for that empty state.

Movement labels and scoreboard light candidates are experimental heuristics. They do not change official scores by themselves.

## Federation pilot slice (October 2026)

Implemented and tested: licensed athlete identity with per-organization
uniqueness, CSV license import with per-line errors, competition entries with
weapon matching, poule generation, standings (formula_version 1),
power-of-two DE draws with byes, winner advancement that refuses tied bouts,
referee assignment with a self-officiating conflict rule, bout completion, and
a competition workspace UI. Verified: `services/api` pytest 22 passed
(includes 6 new federation tests), domain poule/DE unit tests 7 passed,
`apps/web` tsc and vitest passed, and the dashboard, videos, analysis,
performance, and coach flows were re-verified in the browser. The remaining
federation roadmap (seasons, org hierarchy, qualification rules, challenges,
mobile capture, retention) is tracked in `docs/FEDERATION_ROADMAP.md`.
