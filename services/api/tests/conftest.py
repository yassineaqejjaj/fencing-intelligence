import os
from pathlib import Path

os.environ["DATABASE_URL"] = "postgresql+psycopg://fencing:fencing@localhost:5432/fencing_test"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["INLINE_JOBS"] = "true"
os.environ["ENVIRONMENT"] = "test"
os.environ["S3_BUCKET"] = "fencing-test"
os.environ["DATA_IMPORT_ROOT"] = "/tmp/fencing-intelligence-imports"
os.environ["DATASET_MANIFEST_ROOT"] = "/tmp/fencing-intelligence-manifests"
Path("/tmp/fencing-intelligence-imports").mkdir(exist_ok=True)
Path("/tmp/fencing-intelligence-manifests").mkdir(exist_ok=True)
tool_bin = Path("/tmp/fi-bin")
if (tool_bin / "ffmpeg").exists() and (tool_bin / "ffprobe").exists():
    os.environ["PATH"] = str(tool_bin) + os.pathsep + os.environ.get("PATH", "")

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

from fencing_api.database import Base, SessionLocal
from fencing_api.mailer import OUTBOX
from fencing_api.main import app
from fencing_api.seed import seed


def _ensure_database() -> None:
    with psycopg.connect("postgresql://fencing:fencing@localhost:5432/postgres", autocommit=True) as connection:
        exists = connection.execute("SELECT 1 FROM pg_database WHERE datname = 'fencing_test'").fetchone()
        if not exists:
            connection.execute("CREATE DATABASE fencing_test")


def _migrate() -> None:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "head")


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    _ensure_database()
    _migrate()


@pytest.fixture
def client():
    db = SessionLocal()
    table_names = ", ".join(table.name for table in reversed(Base.metadata.sorted_tables))
    db.execute(text(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE"))
    db.commit()
    seed(db)
    db.commit()
    db.close()
    OUTBOX.messages.clear()
    import redis

    redis.Redis.from_url(os.environ["REDIS_URL"]).flushdb()
    with TestClient(app) as test_client:
        yield test_client

