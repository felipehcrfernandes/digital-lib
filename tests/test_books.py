from fastapi.testclient import TestClient


def test_create_book_returns_201_and_persists_data(client: TestClient) -> None:
    payload = {
        "title": "Clean Architecture",
        "author": "Robert C. Martin",
        "isbn": "9780134494166",
        "published_year": 2017,
        "total_copies": 3,
        "available_copies": 3,
    }

    response = client.post("/books", json=payload)

    assert response.status_code == 201

    data = response.json()
    assert data["id"] == 1
    assert data["title"] == "Clean Architecture"
    assert data["author"] == "Robert C. Martin"
    assert data["isbn"] == "9780134494166"
    assert data["total_copies"] == 3
    assert data["available_copies"] == 3


def test_create_book_trims_title_and_author(client: TestClient) -> None:
    payload = {
        "title": "  Crime e Castigo  ",
        "author": "  Dostoevsky  ",
        "isbn": "0123456789",
        "published_year": 1866,
        "total_copies": 1,
        "available_copies": 1,
    }

    response = client.post("/books", json=payload)

    assert response.status_code == 201

    data = response.json()
    assert data["title"] == "Crime e Castigo"
    assert data["author"] == "Dostoevsky"


def test_create_book_with_duplicate_isbn_returns_409(client: TestClient) -> None:
    payload = {
        "title": "Book One",
        "author": "Author One",
        "isbn": "1234567890",
        "published_year": 2020,
        "total_copies": 1,
        "available_copies": 1,
    }

    first_response = client.post("/books", json=payload)
    second_response = client.post("/books", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json() == {
        "detail": "A book with this ISBN already exists"
    }


def test_create_book_with_invalid_inventory_returns_400(client: TestClient) -> None:
    payload = {
        "title": "Inventory Error",
        "author": "Author",
        "isbn": "9876543210",
        "published_year": 2021,
        "total_copies": 1,
        "available_copies": 2,
    }

    response = client.post("/books", json=payload)

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Available copies cannot be greater than total copies"
    }


def test_check_availability_returns_expected_structure(client: TestClient) -> None:
    create_response = client.post(
        "/books",
        json={
            "title": "Available Book",
            "author": "Author",
            "isbn": "1111111111",
            "published_year": 2022,
            "total_copies": 2,
            "available_copies": 2,
        },
    )

    book_id = create_response.json()["id"]

    response = client.get(f"/books/{book_id}/availability")

    assert response.status_code == 200
    assert response.json() == {
        "book_id": book_id,
        "available": True,
        "available_copies": 2,
        "total_copies": 2,
    }


def test_list_books_returns_paginated_response(client: TestClient) -> None:
    client.post(
        "/books",
        json={
            "title": "Book One",
            "author": "Author One",
            "isbn": "2222222222",
            "published_year": 2020,
            "total_copies": 1,
            "available_copies": 1,
        },
    )
    client.post(
        "/books",
        json={
            "title": "Book Two",
            "author": "Author Two",
            "isbn": "3333333333",
            "published_year": 2021,
            "total_copies": 1,
            "available_copies": 1,
        },
    )

    response = client.get("/books?skip=0&limit=1")

    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 2
    assert data["skip"] == 0
    assert data["limit"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Book One"