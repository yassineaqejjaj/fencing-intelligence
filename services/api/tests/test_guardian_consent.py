import pytest
from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from fencing_api.database import SessionLocal
from fencing_api.minors import guardian_consent_granted, is_minor
from fencing_api.models import Video
from fencing_api.retention import purge_expired
from fencing_api.security import utcnow


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def register(client: TestClient, email: str = "guardian@example.com") -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "practice-blade-19",
            "display_name": "Club Coach",
            "organization_name": "Minor Test Club",
            "locale": "en",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    client.headers["X-CSRF-Token"] = body["csrf_token"]
    return body


def test_minor_flag_and_latest_consent_wins(client: TestClient):
    register(client)
    adult = client.post("/api/v1/athletes", json={"display_name": "Adult", "weapon": "epee", "birth_year": 1990}).json()
    assert adult["is_minor"] is False
    assert adult["guardian_consent_granted"] is None
    minor = client.post(
        "/api/v1/athletes",
        json={"display_name": "Cadet", "weapon": "epee", "birth_year": date.today().year - 14, "category": "u15"},
    ).json()
    assert minor["is_minor"] is True
    assert minor["guardian_consent_granted"] is False

    fetched = client.get(f"/api/v1/athletes/{minor['id']}").json()
    assert fetched["guardian_consent_granted"] is False

    grant = client.post(
        f"/api/v1/athletes/{minor['id']}/guardian-consent",
        json={"granted": True, "guardian_name": "Parent", "note": "signed at desk"},
    )
    assert grant.status_code == 200, grant.text
    assert client.get(f"/api/v1/athletes/{minor['id']}").json()["guardian_consent_granted"] is True

    revoke = client.post(f"/api/v1/athletes/{minor['id']}/guardian-consent", json={"granted": False})
    assert revoke.status_code == 200
    assert client.get(f"/api/v1/athletes/{minor['id']}").json()["guardian_consent_granted"] is False

    not_minor = client.post(f"/api/v1/athletes/{adult['id']}/guardian-consent", json={"granted": True})
    assert not_minor.status_code == 422


def test_minor_video_forced_private_and_no_training(client: TestClient, tmp_path):
    register(client)
    minor = client.post(
        "/api/v1/athletes", json={"display_name": "Minor Fencer", "weapon": "epee", "birth_year": date.today().year - 12}
    ).json()
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(bytes.fromhex("00000018667479706d703432") + b"\x00" * 64)

    def upload(**extra):
        with open(clip, "rb") as handle:
            return client.post(
                "/api/v1/videos/upload",
                files={"file": ("clip.mp4", handle, "video/mp4")},
                data={"title": "minor bout", "weapon": "epee", "athlete_id": minor["id"], **extra},
            )

    forced = upload(visibility="club")
    assert forced.status_code == 201, forced.text
    assert forced.json()["video"]["visibility"] == "private"
    assert forced.json()["visibility_forced_private"] is True

    training = upload(training_consent=True)
    assert training.status_code == 422
    assert training.json()["error"]["code"] == "guardian_consent_required"

    client.post(f"/api/v1/athletes/{minor['id']}/guardian-consent", json={"granted": True})
    open_upload = upload(visibility="club")
    assert open_upload.status_code == 201, open_upload.text
    assert open_upload.json()["video"]["visibility"] == "club"


def test_retention_purge_only_expired(client: TestClient, db_session, tmp_path):
    register(client, email="retention@example.com")
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(bytes.fromhex("00000018667479706d703432") + b"\x00" * 64)
    with open(clip, "rb") as handle:
        created = client.post(
            "/api/v1/videos/upload",
            files={"file": ("clip.mp4", handle, "video/mp4")},
            data={"title": "to forget", "weapon": "epee"},
        )
    assert created.status_code == 201, created.text
    video_id = created.json()["video"]["id"]

    video = db_session.scalar(select(Video).where(Video.id == video_id))
    key = video.storage_key
    video.deleted_at = utcnow() - timedelta(days=40)
    db_session.commit()

    preview = purge_expired(db_session, days=30, dry_run=True)
    assert len(preview) == 1 and preview[0]["video_id"] == video_id
    assert client.get(f"/api/v1/videos/{video_id}").status_code == 404  # soft-deleted: hidden but present
    assert db_session.get(Video, video_id) is not None

    assert purge_expired(db_session, days=60, dry_run=False) == []
    assert db_session.get(Video, video_id) is not None

    done = purge_expired(db_session, days=30, dry_run=False)
    assert len(done) == 1
    assert db_session.get(Video, video_id) is None
    from fencing_api.storage import head

    try:
        head(key)
        key_gone = False
    except Exception:
        key_gone = True
    assert key_gone


def test_is_minor_boundaries():
    assert is_minor(None) is False
    assert is_minor(date.today().year - 17) is True
    assert is_minor(date.today().year - 18) is False
    assert guardian_consent_granted.__name__ == "guardian_consent_granted"
