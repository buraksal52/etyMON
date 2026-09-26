from fastapi.testclient import TestClient

from app.main import app


def test_state_changing_request_rejects_unknown_origin() -> None:
    response = TestClient(app).post(
        "/admin/login",
        headers={"Origin": "https://malicious.example"},
        json={"email": "organizer@example.com", "password": "secret"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Request origin is not allowed"


def test_allowed_origin_reaches_application_router() -> None:
    response = TestClient(app).post(
        "/route-that-does-not-exist",
        headers={"Origin": "http://localhost:3000"},
    )

    assert response.status_code == 404
