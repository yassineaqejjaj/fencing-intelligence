from fastapi.testclient import TestClient


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
