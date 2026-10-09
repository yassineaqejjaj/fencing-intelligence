FROM python:3.12-slim-bookworm

RUN apt-get update \
  && apt-get install -y --no-install-recommends ffmpeg \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY packages/fencing-domain packages/fencing-domain
COPY services/video-worker services/video-worker
COPY services/ml-inference services/ml-inference
COPY ml ml
COPY services/api services/api
RUN pip install --no-cache-dir \
  ./packages/fencing-domain \
  ./services/video-worker \
  ./services/ml-inference \
  ./ml \
  ./services/api

WORKDIR /app/services/api
EXPOSE 8000
# Railway injects PORT. SERVICE_ROLE=worker runs Dramatiq from the same image.
CMD ["sh", "-c", "if [ \"$SERVICE_ROLE\" = \"worker\" ]; then exec python -m dramatiq fencing_api.tasks --processes 1 --threads 2; else alembic upgrade head && exec uvicorn fencing_api.main:app --host 0.0.0.0 --port ${PORT:-8000}; fi"]
