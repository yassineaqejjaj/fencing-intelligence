import uuid

from fencing_api.database import SessionLocal
from fencing_api.models import Video

from helpers import register


def _setup(client):
    body = register(client)
    left = client.post("/api/v1/athletes", json={"display_name": "Ada", "weapon": "epee", "dominant_hand": "right"}).json()
    right = client.post("/api/v1/athletes", json={"display_name": "Bea", "weapon": "epee", "dominant_hand": "left"}).json()
    return body, left, right


def _bout(client, left, right, day, sequence):
    bout = client.post("/api/v1/bouts", json={"weapon": "epee", "left_athlete_id": left["id"], "right_athlete_id": right["id"], "started_on": day})
    assert bout.status_code == 201, bout.text
    bout_id = bout.json()["id"]
    for step, letter in enumerate(sequence, start=1):
        scorer, receiver = (left, right) if letter == "L" else (right, left)
        touch = client.post(
            f"/api/v1/bouts/{bout_id}/touches",
            json={"scorer_athlete_id": scorer["id"], "receiver_athlete_id": receiver["id"], "timestamp_ms": step * 1000, "target_area": "weapon_arm" if letter == "R" else "chest", "points": 1},
        )
        assert touch.status_code == 201, touch.text
    return bout_id


def test_intelligence_cards_and_momentum_from_validated_touches(client):
    _body, left, right = _setup(client)
    # Ada trails early and comes back in bout one; loses bout two after a run against her.
    first = _bout(client, left, right, "2026-03-01", "RRLLL")
    _bout(client, left, right, "2026-03-08", "LRRRL")

    empty = client.get(f"/api/v1/athletes/{uuid.uuid4()}/intelligence")
    assert empty.status_code == 404

    response = client.get(f"/api/v1/athletes/{left['id']}/intelligence")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["data_status"] == "ok"
    assert body["formula_version"] == "1"
    assert body["momentum"]["bouts_won"] == 1 and body["momentum"]["bouts_lost"] == 1
    assert body["momentum"]["comebacks"] == 1
    assert body["trend"]["direction"] is None and body["trend"]["reason"] == "insufficient_bouts"
    trailing = body["situations"]["states"]["trailing"]
    assert trailing["scored"] + trailing["conceded"] == trailing["touch_share"]["denominator"]
    codes = {card["code"] for card in body["cards"]}
    assert "comeback" in codes
    assert "conceded_target" in codes  # every conceded touch landed on the weapon arm, 5 samples
    for card in body["cards"]:
        assert card["text_fr"] and card["text_en"] and "denominator" in card["evidence"]
    assert body["opponents"][0]["opponent_id"] == right["id"]
    assert body["opponents"][0]["bouts"] == 2
    assert body["athlete_names"][left["id"]] == "Ada"

    momentum = client.get(f"/api/v1/bouts/{first}/momentum")
    assert momentum.status_code == 200
    timeline = momentum.json()["timeline"]
    assert [(row["left"], row["right"]) for row in timeline] == [(0, 1), (0, 2), (1, 2), (2, 2), (3, 2)]
    assert momentum.json()["lead_changes"] == 1
    assert momentum.json()["right"]["longest_run"] == 2

    foil = client.get(f"/api/v1/athletes/{left['id']}/intelligence", params={"weapon": "foil"})
    assert foil.json()["data_status"] == "no_validated_data"
    assert foil.json()["cards"] == []


def test_review_queue_lists_drafts_and_reject_excludes_from_statistics(client):
    body, left, right = _setup(client)
    org_id = uuid.UUID(body["organization_id"])
    db = SessionLocal()
    try:
        video = Video(
            organization_id=org_id,
            athlete_id=uuid.UUID(left["id"]),
            title="Club night",
            weapon="epee",
            status="ready",
            visibility="club",
            original_filename="x.mp4",
            content_type="video/mp4",
            created_by=uuid.UUID(body["user"]["id"]),
        )
        db.add(video)
        db.commit()
        video_id = str(video.id)
    finally:
        db.close()

    queue = client.get("/api/v1/review-queue")
    assert queue.status_code == 200
    assert queue.json() == {"items": [], "pending_total": 0, "by_source": {}}

    def draft(code: str, start: int):
        response = client.post(
            f"/api/v1/videos/{video_id}/annotations",
            json={"mode": "simplified", "action_type_code": code, "start_ms": start, "end_ms": start + 300, "actor_athlete_id": left["id"], "opponent_athlete_id": right["id"], "outcome": "touch_for"},
        )
        assert response.status_code == 201, response.text
        return response.json()

    first = draft("attack", 100)
    second = draft("flick", 900)
    queue = client.get("/api/v1/review-queue").json()
    assert queue["pending_total"] == 2
    assert [item["id"] for item in queue["items"]] == [second["id"], first["id"]]
    assert queue["items"][0]["video_title"] == "Club night"
    assert queue["items"][0]["actor_name"] == "Ada"
    assert queue["items"][0]["experimental"] is True
    assert queue["items"][0]["action_label_fr"] == "Coup lancé"
    assert queue["by_source"] == {"human": 2}

    rejected = client.post(f"/api/v1/annotations/{second['id']}/reject")
    assert rejected.status_code == 200 and rejected.json()["status"] == "rejected"
    validated = client.post(f"/api/v1/annotations/{first['id']}/validate")
    assert validated.json()["status"] == "validated"
    assert client.get("/api/v1/review-queue").json()["pending_total"] == 0

    stats = client.get(f"/api/v1/athletes/{left['id']}/statistics").json()
    assert stats["combined"]["action_frequency"] == {"attack": 1}
    intelligence = client.get(f"/api/v1/athletes/{left['id']}/intelligence").json()
    assert intelligence["profile"]["total_actions"] == 1
    assert intelligence["profile"]["by_action"] == {"attack": {"attempts": 1, "successes": 1, "success_rate": {"value": 1.0, "numerator": 1, "denominator": 1, "reason": None}}}
    assert intelligence["profile"]["strengths"] == []  # one attempt is below the minimum sample

    versions = client.get(f"/api/v1/annotations/{second['id']}/versions").json()["items"]
    assert len(versions) == 2

    missing = client.post(f"/api/v1/annotations/{uuid.uuid4()}/reject")
    assert missing.status_code == 404
