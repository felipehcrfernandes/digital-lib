from fastapi.testclient import TestClient


def test_health_check_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    assert data["app_name"] == "Digital Library API"
    assert data["version"] == "0.1.0"
    assert data["timestamp"] is not None
    assert data["database"] == {"status": "ok"}
    assert data["metrics"] == {
        "users": 0,
        "books": 0,
        "loans_total": 0,
        "loans_active": 0,
        "loans_overdue": 0,
        "reservations_total": 0,
        "reservations_waiting": 0,
        "reservations_ready_for_pickup": 0,
    }
