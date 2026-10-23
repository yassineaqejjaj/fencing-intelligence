# Fencing Intelligence

<!-- portfolio-summary:start -->

> **Human-validated fencing video analysis** | **Status:** Experimental beta; detection heuristics are not validated refereeing.
>
> [Live application](https://fencing-intelligence.vercel.app) · [Architecture](README.md#run-locally) · [Demo / verification](README.md#what-you-can-do) · [Source code](https://github.com/yassineaqejjaj/fencing-intelligence)

[![GitHub Actions](https://github.com/yassineaqejjaj/fencing-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/yassineaqejjaj/fencing-intelligence/actions/workflows/ci.yml)

<!-- portfolio-summary:end -->


Self-hosted fencing video analysis for épée, foil, and sabre. Coaches and athletes upload video, annotate actions, record touches, and read statistics that come only from validated records.

The application is useful without a trained fencing model. Movement and scoreboard detectors are experimental heuristics. They do not claim recognition accuracy, and they do not decide referee priority.

## What you can do

- Create an account, a club, and athlete profiles.
- Upload a video, transcode it, and play it through a short-lived signed URL.
- Mark actions, touches, and scores.
- Read bout and athlete statistics, including explicit empty states when nothing is validated.
- Generate a PDF report and export JSON or CSV.
- Review dataset licenses with `datasets doctor`.

## Run locally

Requirements: Docker, Python 3.12 or 3.13, [uv](https://docs.astral.sh/uv/), Node.js 22 or newer, pnpm, and FFmpeg with `ffprobe` on `PATH`.

```bash
docker compose up -d postgres redis minio
cd services/api
uv sync
uv run alembic upgrade head
INLINE_JOBS=true uv run uvicorn fencing_api.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```bash
cd apps/web
pnpm install
API_INTERNAL_URL=http://127.0.0.1:8000 pnpm dev
```

Open http://localhost:3000. If another program already uses port 8000 or 3000, start Uvicorn and `pnpm dev` on free ports and set `API_INTERNAL_URL` to the API. Copy `.env.example` when you change hosts or secrets. Development defaults are rejected when `ENVIRONMENT=production`.

`INLINE_JOBS=true` processes video inside the API process. Leave it false and run the worker for anything beyond a local session:

```bash
cd services/api
uv run python -m dramatiq fencing_api.tasks --processes 1 --threads 2
```

## Dataset check

```bash
cd services/api
uv run datasets doctor --root ../../data/datasets
```

External datasets are not downloaded. See `docs/LICENSES.md`.

## Tests

```bash
cd services/api
uv run pytest tests ../../packages/fencing-domain/tests -q
cd ../../apps/web
pnpm exec tsc --noEmit
pnpm test
```

The Python suite needs the Compose services and FFmpeg. It creates the `fencing_test` database.

## License

Original code is Apache-2.0. See `LICENSE` and `docs/LICENSES.md`.
