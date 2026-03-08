from fastapi.testclient import TestClient


def create_user(client: TestClient, *, name: str, email: str) -> dict:
    response = client.post(
        "/users",
        json={
            "name": name,
            "email": email,
        },
    )
    assert response.status_code == 201
    return response.json()


def create_book(
    client: TestClient,
    *,
    title: str,
    author: str,
    isbn: str,
    total_copies: int = 1,
    available_copies: int = 1,
) -> dict:
    response = client.post(
        "/books",
        json={
            "title": title,
            "author": author,
            "isbn": isbn,
            "published_year": 2020,
            "total_copies": total_copies,
            "available_copies": available_copies,
        },
    )
    assert response.status_code == 201
    return response.json()


def create_loan(client: TestClient, *, user_id: int, book_id: int) -> dict:
    response = client.post(
        "/loans",
        json={
            "user_id": user_id,
            "book_id": book_id,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_create_reservation_returns_201_when_book_is_unavailable(client: TestClient) -> None:
    borrower = create_user(client, name="Borrower", email="borrower@example.com")
    waiter = create_user(client, name="Waiter", email="waiter@example.com")
    book = create_book(
        client,
        title="Reserved Book",
        author="Author",
        isbn="9011111111",
        total_copies=1,
        available_copies=1,
    )

    create_loan(client, user_id=borrower["id"], book_id=book["id"])

    response = client.post(
        "/reservations",
        json={
            "user_id": waiter["id"],
            "book_id": book["id"],
        },
    )

    assert response.status_code == 201

    data = response.json()
    assert data["user_id"] == waiter["id"]
    assert data["book_id"] == book["id"]
    assert data["status"] == "WAITING"
    assert data["available_at"] is None
    assert data["expires_at"] is None


def test_create_reservation_returns_400_when_book_is_available(client: TestClient) -> None:
    user = create_user(client, name="Felipe", email="felipe@example.com")
    book = create_book(
        client,
        title="Available Book",
        author="Author",
        isbn="9011111112",
        total_copies=1,
        available_copies=1,
    )

    response = client.post(
        "/reservations",
        json={
            "user_id": user["id"],
            "book_id": book["id"],
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Book is currently available and does not need a reservation"
    }


def test_create_reservation_returns_400_when_user_already_has_active_reservation_for_book(client: TestClient) -> None:
    borrower = create_user(client, name="Borrower", email="borrower@example.com")
    waiter = create_user(client, name="Waiter", email="waiter@example.com")
    book = create_book(
        client,
        title="Duplicate Reservation Book",
        author="Author",
        isbn="9011111113",
        total_copies=1,
        available_copies=1,
    )

    create_loan(client, user_id=borrower["id"], book_id=book["id"])

    first_response = client.post(
        "/reservations",
        json={
            "user_id": waiter["id"],
            "book_id": book["id"],
        },
    )
    second_response = client.post(
        "/reservations",
        json={
            "user_id": waiter["id"],
            "book_id": book["id"],
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 400
    assert second_response.json() == {
        "detail": "User already has an active reservation for this book"
    }


def test_return_loan_promotes_next_reservation_to_ready_for_pickup(client: TestClient) -> None:
    borrower = create_user(client, name="Borrower", email="borrower@example.com")
    first_waiter = create_user(client, name="First Waiter", email="first@example.com")
    second_waiter = create_user(client, name="Second Waiter", email="second@example.com")
    book = create_book(
        client,
        title="Queue Book",
        author="Author",
        isbn="9011111114",
        total_copies=1,
        available_copies=1,
    )

    loan = create_loan(client, user_id=borrower["id"], book_id=book["id"])

    first_reservation = client.post(
        "/reservations",
        json={
            "user_id": first_waiter["id"],
            "book_id": book["id"],
        },
    )
    second_reservation = client.post(
        "/reservations",
        json={
            "user_id": second_waiter["id"],
            "book_id": book["id"],
        },
    )

    assert first_reservation.status_code == 201
    assert second_reservation.status_code == 201

    return_response = client.post(f"/loans/{loan['id']}/return")
    assert return_response.status_code == 200

    reservation_response = client.get(f"/reservations/{first_reservation.json()['id']}")
    assert reservation_response.status_code == 200

    data = reservation_response.json()
    assert data["status"] == "READY_FOR_PICKUP"
    assert data["available_at"] is not None
    assert data["expires_at"] is not None

    second_reservation_response = client.get(f"/reservations/{second_reservation.json()['id']}")
    assert second_reservation_response.status_code == 200
    assert second_reservation_response.json()["status"] == "WAITING"


def test_cancel_ready_for_pickup_reservation_promotes_next_waiting_one(client: TestClient) -> None:
    borrower = create_user(client, name="Borrower", email="borrower@example.com")
    first_waiter = create_user(client, name="First Waiter", email="first@example.com")
    second_waiter = create_user(client, name="Second Waiter", email="second@example.com")
    book = create_book(
        client,
        title="Promotion Book",
        author="Author",
        isbn="9011111115",
        total_copies=1,
        available_copies=1,
    )

    loan = create_loan(client, user_id=borrower["id"], book_id=book["id"])

    first_reservation = client.post(
        "/reservations",
        json={
            "user_id": first_waiter["id"],
            "book_id": book["id"],
        },
    ).json()
    second_reservation = client.post(
        "/reservations",
        json={
            "user_id": second_waiter["id"],
            "book_id": book["id"],
        },
    ).json()

    client.post(f"/loans/{loan['id']}/return")

    cancel_response = client.post(f"/reservations/{first_reservation['id']}/cancel")
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "CANCELLED"

    updated_second = client.get(f"/reservations/{second_reservation['id']}")
    assert updated_second.status_code == 200

    second_data = updated_second.json()
    assert second_data["status"] == "READY_FOR_PICKUP"
    assert second_data["available_at"] is not None
    assert second_data["expires_at"] is not None


def test_list_user_reservations_returns_paginated_response(client: TestClient) -> None:
    borrower = create_user(client, name="Borrower", email="borrower@example.com")
    waiter = create_user(client, name="Waiter", email="waiter@example.com")

    first_book = create_book(
        client,
        title="Book One",
        author="Author",
        isbn="9011111116",
        total_copies=1,
        available_copies=1,
    )
    second_book = create_book(
        client,
        title="Book Two",
        author="Author",
        isbn="9011111117",
        total_copies=1,
        available_copies=1,
    )

    create_loan(client, user_id=borrower["id"], book_id=first_book["id"])
    create_loan(client, user_id=borrower["id"], book_id=second_book["id"])

    client.post("/reservations", json={"user_id": waiter["id"], "book_id": first_book["id"]})
    client.post("/reservations", json={"user_id": waiter["id"], "book_id": second_book["id"]})

    response = client.get(f"/reservations/users/{waiter['id']}?skip=0&limit=1")

    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 2
    assert data["skip"] == 0
    assert data["limit"] == 1
    assert len(data["items"]) == 1