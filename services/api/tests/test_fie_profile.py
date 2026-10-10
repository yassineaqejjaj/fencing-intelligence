from fastapi.testclient import TestClient

from fencing_api.services import fie_profiles

WALID = {
    "id": 30384,
    "firstName": "Walid",
    "lastName": "EL FALJI",
    "name": "EL FALJI Walid",
    "country": "Morocco",
    "countryCode": "MAR",
    "weapon": "S",
    "gender": "M",
    "points": "0.000",
    "date": "1994-10-25",
    "category": "S",
    "hand": "R",
    "height": None,
    "rank": 770,
    "season": 2027,
    "licenseNumber": "25101994003",
    "licenseStatus": "Valid",
    "biography": "Do not keep this prose.",
    "image": "https://static.fie.org/uploads/1/9769-30384.jpg",
    "ranking": [{"rank": 119, "point": "8.000", "weapon": "S", "season": 2022, "category": "S"}],
    "olympicMedals": {"gold": 0, "silver": 0, "bronze": 0},
    "olympicTeamMedals": {"gold": 0, "silver": 0, "bronze": 0},
    "worldChampionshipMedals": {"gold": 0, "silver": 0, "bronze": 0},
    "worldChampionshipTeamMedals": {"gold": 0, "silver": 0, "bronze": 0},
    "medals": [
        {
            "competitionName": "Championnats d'Afrique",
            "medal": "bronze",
            "location": "Casablanca",
            "country": "Morocco",
            "date": "2024-06-09",
            "season": 2024,
        }
    ],
    "futureCompetitions": [
        {
            "name": "Cairo World Cup 2026",
            "city": "Cairo",
            "country": "EGY",
            "type": "World Cup",
            "startDate": "2026-11-12",
            "endDate": "2026-11-15",
            "coverUrl": "https://static.fie.org/should-not-be-stored.jpg",
        }
    ],
}

OPPONENTS = {
    "totalFound": 1,
    "page": 1,
    "pageSize": 100,
    "items": [
        {
            "id": 65508,
            "name": "WANG Hengyu",
            "nationality": "CHINA",
            "victories": 0,
            "defeats": 1,
            "events": [
                {
                    "name": "Coupe du Monde",
                    "date": "2026-05-22 00:00:00",
                    "location": "Cairo",
                    "country": "EGYPT",
                    "season": 2026,
                    "weapon": "S",
                    "fencer1": {"id": 30384, "score": 3, "isWinner": False},
                    "fencer2": {"id": 65508, "score": 5, "isWinner": True},
                }
            ],
        }
    ],
}


def register(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "fie-club@example.com",
            "password": "practice-blade-19",
            "display_name": "Club Admin",
            "organization_name": "Salle FIE",
            "locale": "en",
        },
    )
    assert response.status_code == 201, response.text
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]


def test_search_returns_identity_without_license(client: TestClient, monkeypatch):
    register(client)

    def fake_get(path, params=None):
        assert path == "/fencers-all"
        return {
            "items": [
                {
                    "id": 30384,
                    "firstName": "Walid",
                    "lastName": "EL FALJI",
                    "country": "Morocco",
                    "countryCode": "MAR",
                    "weapon": "S",
                    "gender": "M",
                    "rank": 770,
                    "points": "0.000",
                    "age": 31,
                    "licenseNumber": "25101994003",
                    "date": "1994-10-25",
                }
            ]
        }

    monkeypatch.setattr(fie_profiles, "_get", fake_get)
    response = client.get("/api/v1/federation/fie/search", params={"q": "Falji"})
    assert response.status_code == 200, response.text
    item = response.json()["items"][0]
    assert item["name"] == "Walid El Falji"
    assert item["weapon"] == "sabre"
    assert item["rank"] == 770
    assert "license" not in item
    assert "1994" not in str(item)


def test_create_from_fie_stores_record_and_skips_prose(client: TestClient, monkeypatch):
    register(client)

    def fake_get(path, params=None):
        if path == "/fencer/30384":
            return WALID
        if path == "/fencer/30384/opponents":
            return OPPONENTS
        raise AssertionError(path)

    monkeypatch.setattr(fie_profiles, "_get", fake_get)
    created = client.post("/api/v1/federation/fie/athletes", json={"profile_url": "https://fie.org/athletes/30384"})
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["display_name"] == "Walid El Falji"
    assert body["weapon"] == "sabre"
    assert body["country"] == "Morocco"
    assert body["dominant_hand"] == "right"
    assert body["license_number"] == "25101994003"
    assert body["birth_year"] == 1994
    assert body["category"] == "senior"
    profile = body["fie_profile"]
    assert profile["rank"] == 770
    assert profile["source_url"] == "https://fie.org/athletes/30384"
    assert profile["record"] == {"wins": 0, "losses": 1, "bouts": 1, "opponents": 1, "truncated": False}
    assert profile["bouts"][0]["for_score"] == 3
    assert profile["bouts"][0]["against_score"] == 5
    assert profile["medals"][0]["medal"] == "bronze"
    assert profile["upcoming"][0]["name"] == "Cairo World Cup 2026"
    assert "coverUrl" not in profile["upcoming"][0]
    assert "biography" not in profile
    assert "image" not in profile
    again = client.post("/api/v1/federation/fie/athletes", json={"fie_id": 30384})
    assert again.status_code == 409
