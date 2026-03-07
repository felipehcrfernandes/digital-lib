from fastapi.testclient import TestClient


def test_create_user_returns_201_and_persists_data(client: TestClient) -> None:
    payload = {
        "name": "Felipe Silva",
        "email": "felipe@example.com",
    }

    response = client.post("/users", json=payload)

    assert response.status_code == 201

    data = response.json()
    assert data["id"] == 1
    assert data["name"] == "Felipe Silva"
    assert data["email"] == "felipe@example.com"
    assert data["is_active"] is True


def test_create_user_trims_name_input(client: TestClient) -> None:
    payload = {
        "name": "  João Silva  ",
        "email": "joao@example.com",
    }

    response = client.post("/users", json=payload)

    assert response.status_code == 201
    assert response.json()["name"] == "João Silva"


def test_create_user_with_duplicate_email_returns_409(client: TestClient) -> None:
    payload = {
        "name": "Felipe Silva",
        "email": "felipe@example.com",
    }

    first_response = client.post("/users", json=payload)
    second_response = client.post("/users", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json() == {
        "detail": "A user with this email already exists"
    }


def test_get_user_returns_404_for_unknown_id(client: TestClient) -> None:
    response = client.get("/users/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}


def test_list_users_returns_paginated_response(client: TestClient) -> None:
    client.post(
        "/users",
        json={"name": "User One", "email": "user1@example.com"},
    )
    client.post(
        "/users",
        json={"name": "User Two", "email": "user2@example.com"},
    )

    response = client.get("/users?skip=0&limit=1")

    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 2
    assert data["skip"] == 0
    assert data["limit"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["email"] == "user1@example.com"