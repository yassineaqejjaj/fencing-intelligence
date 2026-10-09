import json
import shutil
import subprocess
from pathlib import Path

import pytest

from fastapi.testclient import TestClient

from fencing_api.mailer import OUTBOX


def register(client: TestClient, email: str = "coach@example.com", organization: str = "Salle A") -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "practice-blade-19",
            "display_name": "Coach",
            "organization_name": organization,
            "locale": "en",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    client.headers["X-CSRF-Token"] = body["csrf_token"]
    return body


def test_register_login_and_csrf(client):
    body = register(client)
    assert body["user"]["email"] == "coach@example.com"
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    client.headers.pop("X-CSRF-Token")
    denied = client.post("/api/v1/clubs", json={"name": "No token"})
    assert denied.status_code == 403
    bad = client.post("/api/v1/auth/login", json={"email": "coach@example.com", "password": "wrong-password-1"})
    assert bad.status_code == 401


def test_password_reset_uses_mail_without_returning_the_token(client):
    register(client, email="reset@example.com")
    client.post("/api/v1/auth/logout")
    forgotten = client.post("/api/v1/auth/forgot-password", json={"email": "reset@example.com"})
    assert forgotten.status_code == 200
    assert "token" not in forgotten.json()
    assert OUTBOX.messages
    link = OUTBOX.messages[-1]["body"]
    token = link.split("token=")[1].strip()
    reset = client.post("/api/v1/auth/reset-password", json={"token": token, "password": "new-practice-19"})
    assert reset.status_code == 200
    login = client.post("/api/v1/auth/login", json={"email": "reset@example.com", "password": "new-practice-19"})
    assert login.status_code == 200


def test_manual_analysis_statistics_report_and_export(client, tmp_path):
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        pytest.skip("ffmpeg is not installed")
    sample = tmp_path / "bout.mp4"
    subprocess.run(
        [ffmpeg, "-y", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=30:duration=1", "-pix_fmt", "yuv420p", str(sample)],
        check=True,
        capture_output=True,
    )
    register(client)
    club = client.post("/api/v1/clubs", json={"name": "Salle Nord", "country": "FR", "city": "Lille"})
    assert club.status_code == 201
    left = client.post("/api/v1/athletes", json={"display_name": "Ada", "weapon": "epee", "club_id": club.json()["id"], "dominant_hand": "right"})
    right = client.post("/api/v1/athletes", json={"display_name": "Bea", "weapon": "epee", "dominant_hand": "left"})
    assert left.status_code == 201 and right.status_code == 201
    bout = client.post(
        "/api/v1/bouts",
        json={"weapon": "epee", "left_athlete_id": left.json()["id"], "right_athlete_id": right.json()["id"], "started_on": "2026-03-01"},
    )
    assert bout.status_code == 201
    with sample.open("rb") as handle:
        uploaded = client.post(
            "/api/v1/videos/upload",
            data={
                "title": "Pool bout",
                "weapon": "epee",
                "bout_id": bout.json()["id"],
                "athlete_id": left.json()["id"],
                "visibility": "private",
            },
            files={"file": ("bout.mp4", handle, "video/mp4")},
        )
    assert uploaded.status_code == 201, uploaded.text
    video = uploaded.json()["video"]
    assert video["status"] == "ready"
    assert video["fps"] > 0
    playback = client.get(f"/api/v1/videos/{video['id']}/playback")
    assert playback.status_code == 200
    assert "X-Amz-Signature" in playback.json()["url"] or "Signature=" in playback.json()["url"]
    annotation = client.post(
        f"/api/v1/videos/{video['id']}/annotations",
        json={
            "mode": "simplified",
            "action_type_code": "attack",
            "start_ms": 100,
            "end_ms": 400,
            "actor_athlete_id": left.json()["id"],
            "opponent_athlete_id": right.json()["id"],
            "outcome": "touch_for",
            "target_area": "weapon_arm",
            "piste_position": 0.42,
            "status": "validated",
        },
    )
    assert annotation.status_code == 201, annotation.text
    versions = client.get(f"/api/v1/annotations/{annotation.json()['id']}/versions")
    assert versions.json()["items"]
    touch = client.post(
        f"/api/v1/bouts/{bout.json()['id']}/touches",
        json={
            "scorer_athlete_id": left.json()["id"],
            "receiver_athlete_id": right.json()["id"],
            "timestamp_ms": 400,
            "target_area": "weapon_arm",
            "video_id": video["id"],
            "points": 1,
        },
    )
    assert touch.status_code == 201
    assert touch.json()["bout"]["left"]["score"] == 1
    score = client.post(f"/api/v1/bouts/{bout.json()['id']}/score", json={"left_score": 1, "right_score": 0, "timestamp_ms": 500})
    assert score.status_code == 200
    stats = client.get(f"/api/v1/athletes/{left.json()['id']}/statistics")
    assert stats.status_code == 200
    body = stats.json()
    assert body["data_status"] == "ok"
    assert body["combined"]["touches_scored"] == 1
    assert body["combined"]["offensive_success_rate"]["value"] == 1
    bout_stats = client.get(f"/api/v1/bouts/{bout.json()['id']}/statistics")
    assert bout_stats.json()["data_status"] == "ok"
    assert len(bout_stats.json()["score_progression"]) >= 1
    report = client.post("/api/v1/reports", json={"kind": "athlete", "athlete_id": left.json()["id"], "title": "Ada bout"})
    assert report.status_code == 201, report.text
    download = client.get(f"/api/v1/reports/{report.json()['id']}/download")
    assert download.status_code == 200
    assert "X-Amz-Signature" in download.json()["url"] or "Signature=" in download.json()["url"]
    exported = client.get(f"/api/v1/athletes/{left.json()['id']}/export.json")
    assert exported.status_code == 200
    assert exported.json()["statistics"]["combined"]["touches_scored"] == 1
    csv_export = client.get(f"/api/v1/athletes/{left.json()['id']}/export.csv")
    assert "attack" in csv_export.text


def test_tenant_isolation(client):
    from fastapi.testclient import TestClient

    from fencing_api.main import app

    register(client, email="a@example.com", organization="Org A")
    athlete = client.post("/api/v1/athletes", json={"display_name": "Secret", "weapon": "foil"})
    assert athlete.status_code == 201
    with TestClient(app) as other:
        register(other, email="b@example.com", organization="Org B")
        hidden = other.get(f"/api/v1/athletes/{athlete.json()['id']}")
        assert hidden.status_code == 404
        listing = other.get("/api/v1/athletes")
        assert listing.json()["total"] == 0


def test_empty_statistics_are_not_a_performance(client):
    register(client)
    athlete = client.post("/api/v1/athletes", json={"display_name": "No data", "weapon": "sabre"})
    stats = client.get(f"/api/v1/athletes/{athlete.json()['id']}/statistics")
    assert stats.json()["data_status"] == "no_validated_data"
    assert stats.json()["combined"]["offensive_success_rate"]["value"] is None
    recommendations = client.get(f"/api/v1/athletes/{athlete.json()['id']}/recommendations")
    assert recommendations.json()["items"] == []


def test_ready_endpoint(client):
    ready = client.get("/ready")
    assert ready.status_code == 200
    assert ready.json()["checks"]["database"] is True
    assert ready.json()["checks"]["object_storage"] is True
