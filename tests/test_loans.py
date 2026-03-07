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


def test_create_loan_reduces_book_availability(client: TestClient) -> None:
    user = create_user(client, name="Felipe", email="felipe@example.com")
    book = create_book(
        client,
        title="Clean Code",
        author="Robert C. Martin",
        isbn="9780132350884",
        total_copies=2,
        available_copies=2,
    )

    response = client.post(
        "/loans",
        json={
            "user_id": user["id"],
            "book_id": book["id"],
        },
    )

    assert response.status_code == 201

    loan = response.json()
    assert loan["user_id"] == user["id"]
    assert loan["book_id"] == book["id"]
    assert loan["status"] == "ACTIVE"

    availability_response = client.get(f"/books/{book['id']}/availability")
    assert availability_response.status_code == 200
    assert availability_response.json()["available_copies"] == 1


def test_create_loan_returns_400_when_book_is_unavailable(client: TestClient) -> None:
    user = create_user(client, name="Felipe", email="felipe@example.com")
    book = create_book(
        client,
        title="Unavailable Book",
        author="Author",
        isbn="1111111111",
        total_copies=1,
        available_copies=0,
    )

    response = client.post(
        "/loans",
        json={
            "user_id": user["id"],
            "book_id": book["id"],
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Book is not available for loan"
    }


def test_create_loan_returns_400_when_user_reaches_limit(client: TestClient) -> None:
    user = create_user(client, name="Felipe", email="felipe@example.com")

    books = [
        create_book(client, title="Book 1", author="Author", isbn="1000000001"),
        create_book(client, title="Book 2", author="Author", isbn="1000000002"),
        create_book(client, title="Book 3", author="Author", isbn="1000000003"),
        create_book(client, title="Book 4", author="Author", isbn="1000000004"),
    ]

    for book in books[:3]:
        response = client.post(
            "/loans",
            json={
                "user_id": user["id"],
                "book_id": book["id"],
            },
        )
        assert response.status_code == 201

    fourth_response = client.post(
        "/loans",
        json={
            "user_id": user["id"],
            "book_id": books[3]["id"],
        },
    )

    assert fourth_response.status_code == 400
    assert fourth_response.json() == {
        "detail": "User has reached the maximum number of active loans"
    }


def test_return_loan_marks_it_returned_and_restores_availability(client: TestClient) -> None:
    user = create_user(client, name="Felipe", email="felipe@example.com")
    book = create_book(
        client,
        title="Returnable Book",
        author="Author",
        isbn="2222222222",
        total_copies=1,
        available_copies=1,
    )

    loan_response = client.post(
        "/loans",
        json={
            "user_id": user["id"],
            "book_id": book["id"],
        },
    )
    loan_id = loan_response.json()["id"]

    response = client.post(f"/loans/{loan_id}/return")

    assert response.status_code == 200

    loan = response.json()
    assert loan["status"] == "RETURNED"
    assert loan["return_date"] is not None
    assert loan["fine_amount"] == "0.00"

    availability_response = client.get(f"/books/{book['id']}/availability")
    assert availability_response.status_code == 200
    assert availability_response.json()["available_copies"] == 1


def test_returning_same_loan_twice_returns_400(client: TestClient) -> None:
    user = create_user(client, name="Felipe", email="felipe@example.com")
    book = create_book(
        client,
        title="Book",
        author="Author",
        isbn="3333333333",
    )

    loan_response = client.post(
        "/loans",
        json={
            "user_id": user["id"],
            "book_id": book["id"],
        },
    )
    loan_id = loan_response.json()["id"]

    first_return = client.post(f"/loans/{loan_id}/return")
    second_return = client.post(f"/loans/{loan_id}/return")

    assert first_return.status_code == 200
    assert second_return.status_code == 400
    assert second_return.json() == {
        "detail": "Loan has already been returned"
    }


def test_list_loans_returns_paginated_response(client: TestClient) -> None:
    user = create_user(client, name="Felipe", email="felipe@example.com")
    book_one = create_book(client, title="Book 1", author="Author", isbn="4444444441")
    book_two = create_book(client, title="Book 2", author="Author", isbn="4444444442")

    client.post("/loans", json={"user_id": user["id"], "book_id": book_one["id"]})
    client.post("/loans", json={"user_id": user["id"], "book_id": book_two["id"]})

    response = client.get("/loans?skip=0&limit=1")

    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 2
    assert data["skip"] == 0
    assert data["limit"] == 1
    assert len(data["items"]) == 1


def test_list_user_loans_returns_paginated_response(client: TestClient) -> None:
    user = create_user(client, name="Felipe", email="felipe@example.com")
    book_one = create_book(client, title="Book 1", author="Author", isbn="5555555551")
    book_two = create_book(client, title="Book 2", author="Author", isbn="5555555552")

    client.post("/loans", json={"user_id": user["id"], "book_id": book_one["id"]})
    client.post("/loans", json={"user_id": user["id"], "book_id": book_two["id"]})

    response = client.get(f"/users/{user['id']}/loans?skip=0&limit=1")

    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 2
    assert data["skip"] == 0
    assert data["limit"] == 1
    assert len(data["items"]) == 1

def test_renew_loan_extends_due_date_and_increments_renewal_count(client: TestClient) -> None:
    user = create_user(client, name="Felipe", email="felipe@example.com")
    book = create_book(
        client,
        title="Renewable Book",
        author="Author",
        isbn="6666666666",
    )

    loan_response = client.post(
        "/loans",
        json={
            "user_id": user["id"],
            "book_id": book["id"],
        },
    )
    loan = loan_response.json()

    response = client.post(f"/loans/{loan['id']}/renew")

    assert response.status_code == 200

    renewed = response.json()
    assert renewed["renewal_count"] == 1
    assert renewed["due_date"] != loan["due_date"]
    assert renewed["status"] == "ACTIVE"


def test_renew_loan_returns_400_when_limit_is_reached(client: TestClient) -> None:
    user = create_user(client, name="Felipe", email="felipe@example.com")
    book = create_book(
        client,
        title="Renew Limit Book",
        author="Author",
        isbn="7777777777",
    )

    loan_response = client.post(
        "/loans",
        json={
            "user_id": user["id"],
            "book_id": book["id"],
        },
    )
    loan_id = loan_response.json()["id"]

    first_renewal = client.post(f"/loans/{loan_id}/renew")
    second_renewal = client.post(f"/loans/{loan_id}/renew")

    assert first_renewal.status_code == 200
    assert second_renewal.status_code == 400
    assert second_renewal.json() == {
        "detail": "Loan renewal limit reached"
    }


def test_returned_loan_cannot_be_renewed(client: TestClient) -> None:
    user = create_user(client, name="Felipe", email="felipe@example.com")
    book = create_book(
        client,
        title="Returned Book",
        author="Author",
        isbn="8888888888",
    )

    loan_response = client.post(
        "/loans",
        json={
            "user_id": user["id"],
            "book_id": book["id"],
        },
    )
    loan_id = loan_response.json()["id"]

    client.post(f"/loans/{loan_id}/return")
    response = client.post(f"/loans/{loan_id}/renew")

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Returned loans cannot be renewed"
    }