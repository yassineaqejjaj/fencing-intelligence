import uuid

from fastapi.testclient import TestClient


def register(client: TestClient, email: str = "fede@example.com", organization: str = "Federation") -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "practice-blade-19",
            "display_name": "Fed Admin",
            "organization_name": organization,
            "locale": "en",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    client.headers["X-CSRF-Token"] = body["csrf_token"]
    return body


def make_athlete(client: TestClient, name: str, **extra) -> dict:
    payload = {"display_name": name, "weapon": "epee", "dominant_hand": "right"}
    payload.update(extra)
    response = client.post("/api/v1/athletes", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def make_competition(client: TestClient, name: str = "Regional Open") -> dict:
    response = client.post("/api/v1/competitions", json={"name": name, "weapon": "epee"})
    assert response.status_code == 201, response.text
    return response.json()


def test_license_identity_and_duplicates(client: TestClient):
    register(client)
    first = make_athlete(client, "Licensed One", license_number="FRA-001", birth_year=2008, category="u17")
    assert first["license_number"] == "FRA-001"
    assert first["category"] == "u17"
    duplicate = client.post("/api/v1/athletes", json={"display_name": "Copy", "weapon": "epee", "license_number": "FRA-001"})
    assert duplicate.status_code == 409
    bad_category = client.post("/api/v1/athletes", json={"display_name": "Bad", "weapon": "epee", "category": "pro"})
    assert bad_category.status_code == 422
    bad_year = client.post("/api/v1/athletes", json={"display_name": "Old", "weapon": "epee", "birth_year": 1800})
    assert bad_year.status_code == 422
    other_org = register(client, email="other@example.com", organization="Other League")
    assert other_org["user"]["email"] == "other@example.com"
    reused = client.post("/api/v1/athletes", json={"display_name": "Same license", "weapon": "epee", "license_number": "FRA-001"})
    assert reused.status_code == 201


def test_csv_import_creates_clubs_and_reports_errors(client: TestClient):
    register(client)
    csv_text = (
        "display_name,weapon,license_number,birth_year,category,club,country,dominant_hand\n"
        "Anna,epee,FRA-010,2009,u15,Salle Nord,FR,right\n"
        "Bob,epee,FRA-011,2010,u15,Salle Nord,FR,left\n"
        "Broken,epee,FRA-012,not-a-year,u15,Salle Nord,FR,right\n"
        "Anna Updated,epee,FRA-010,2009,u15,Salle Nord,FR,right\n"
    )
    response = client.post("/api/v1/athletes/import", json={"csv_text": csv_text})
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["created"] == 2
    assert body["updated"] == 1
    assert body["skipped"] == 1
    assert body["errors"]
    clubs = client.get("/api/v1/clubs").json()
    assert any(club["name"] == "Salle Nord" for club in clubs["items"])
    athletes = client.get("/api/v1/athletes").json()
    assert any(item["display_name"] == "Anna Updated" for item in athletes["items"])


def test_poules_standings_and_de_draw(client: TestClient):
    register(client)
    competition = make_competition(client)
    athletes = [make_athlete(client, f"Fencer {index}", license_number=f"FRA-{100 + index}") for index in range(8)]
    for athlete in athletes:
        entered = client.post(f"/api/v1/competitions/{competition['id']}/entries", json={"athlete_id": athlete["id"]})
        assert entered.status_code == 201, entered.text
    duplicate = client.post(f"/api/v1/competitions/{competition['id']}/entries", json={"athlete_id": athletes[0]["id"]})
    assert duplicate.status_code == 422
    poules = client.post(f"/api/v1/competitions/{competition['id']}/poules", json={"poule_size": 4})
    assert poules.status_code == 201, poules.text
    assert poules.json()["bouts"] == 12
    again = client.post(f"/api/v1/competitions/{competition['id']}/poules", json={"poule_size": 4})
    assert again.status_code == 422
    withdrawal = client.delete(f"/api/v1/competitions/{competition['id']}/entries/{athletes[0]['id']}")
    assert withdrawal.status_code == 422

    bouts = client.get("/api/v1/bouts").json()["items"]
    poule_bouts = [bout for bout in bouts if bout["competition_id"] == competition["id"]]
    assert all(bout["round"] == "poule" and bout["score_limit"] == 5 for bout in poule_bouts)
    for bout in poule_bouts:
        client.post(f"/api/v1/bouts/{bout['id']}/score", json={"left_score": 5, "right_score": 3})
        done = client.post(f"/api/v1/bouts/{bout['id']}/complete")
        assert done.status_code == 200
    table = client.get(f"/api/v1/competitions/{competition['id']}/standings").json()
    assert len(table["items"]) == 8
    assert table["formula_version"] == 1
    assert table["items"][0]["victories"] >= table["items"][-1]["victories"]

    draw = client.post(f"/api/v1/competitions/{competition['id']}/de", json={"size": 8, "use_standings": True})
    assert draw.status_code == 201, draw.text
    assert len(draw.json()["bouts"]) == 4


def test_wrong_weapon_entry_rejected(client: TestClient):
    register(client)
    competition = make_competition(client)
    foil = make_athlete(client, "Foilist", weapon="foil")
    response = client.post(f"/api/v1/competitions/{competition['id']}/entries", json={"athlete_id": foil["id"]})
    assert response.status_code == 422


def test_de_advance_requires_decisive_scores(client: TestClient):
    register(client)
    competition = make_competition(client)
    athletes = [make_athlete(client, f"Duelist {index}") for index in range(4)]
    for athlete in athletes:
        client.post(f"/api/v1/competitions/{competition['id']}/entries", json={"athlete_id": athlete["id"]})
    draw = client.post(f"/api/v1/competitions/{competition['id']}/de", json={"size": 4, "use_standings": False})
    assert draw.status_code == 201, draw.text
    bouts = draw.json()["bouts"]
    assert len(bouts) == 2
    first, second = bouts[0]["id"], bouts[1]["id"]
    client.post(f"/api/v1/bouts/{first}/score", json={"left_score": 15, "right_score": 12})
    client.post(f"/api/v1/bouts/{first}/complete")
    client.post(f"/api/v1/bouts/{second}/score", json={"left_score": 10, "right_score": 10})
    client.post(f"/api/v1/bouts/{second}/complete")
    blocked = client.post(f"/api/v1/competitions/{competition['id']}/de/next")
    assert blocked.status_code == 422
    client.post(f"/api/v1/bouts/{second}/score", json={"left_score": 9, "right_score": 15})
    advanced = client.post(f"/api/v1/competitions/{competition['id']}/de/next")
    assert advanced.status_code == 201, advanced.text
    assert advanced.json()["bouts"][0]["label"].startswith("Final")
    final_blocked = client.post(f"/api/v1/competitions/{competition['id']}/de/next")
    assert final_blocked.status_code == 422


def test_referee_assignment_and_conflict(client: TestClient):
    body = register(client)
    me = uuid.UUID(body["user"]["id"])
    left = make_athlete(client, "Lefty")
    right = make_athlete(client, "Righty", user_id=str(me))
    bout = client.post(
        "/api/v1/bouts",
        json={"weapon": "epee", "left_athlete_id": left["id"], "right_athlete_id": right["id"]},
    ).json()
    conflict = client.patch(f"/api/v1/bouts/{bout['id']}/referee", json={"user_id": str(me)})
    assert conflict.status_code == 422
    neutral_left = make_athlete(client, "Neutral Left")
    neutral_right = make_athlete(client, "Neutral Right")
    neutral = client.post(
        "/api/v1/bouts",
        json={"weapon": "epee", "left_athlete_id": neutral_left["id"], "right_athlete_id": neutral_right["id"]},
    ).json()
    assigned = client.patch(f"/api/v1/bouts/{neutral['id']}/referee", json={"user_id": str(me)})
    assert assigned.status_code == 200, assigned.text
    fetched = client.get(f"/api/v1/bouts/{neutral['id']}").json()
    assert fetched["referee_user_id"] == str(me)
    cleared = client.patch(f"/api/v1/bouts/{neutral['id']}/referee", json={"user_id": None})
    assert cleared.status_code == 200
    assert client.get(f"/api/v1/bouts/{neutral['id']}").json()["referee_user_id"] is None
