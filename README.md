# Digital Library API

REST API for managing a digital library, including users, books, and loans.

This project was built as a technical case focused on software architecture, design patterns, business rules, validation, and API quality in Python.

## Current Status

Implemented so far:

- User management
- Book catalog management
- Loan creation and return flow
- Loan renewal flow
- Loan history per user
- Active and overdue loan listing
- Book availability checks
- Global error handling
- Input validation and normalization
- Pagination on list endpoints
- Structured JSON logging
- Automated unit and integration tests with pytest
- Rate limiting on write endpoints
- Automatic Swagger/OpenAPI documentation

Planned next steps:

- Additional differentials
- Docker setup
- Postman collection

## Tech Stack

- Python 3.11
- FastAPI
- SQLAlchemy 2.0
- Pydantic v2
- SQLite
- Uvicorn
- uv

## Why These Choices

### FastAPI

FastAPI was chosen because it provides:

- automatic OpenAPI/Swagger documentation
- strong request and response validation
- dependency injection
- a clean fit for layered architecture

This keeps the focus on domain design and business rules instead of framework boilerplate.

### SQLAlchemy

SQLAlchemy was chosen as the ORM because it is mature, widely used, and supports a clean persistence layer through repositories.

### SQLite

SQLite was chosen for simplicity and fast evaluation. It allows the project to run with zero database setup while still supporting a realistic relational model.

This was a deliberate choice for the case: it reduces execution friction for reviewers while keeping the design production-conscious through SQLAlchemy and configuration abstraction. The priority was business completeness, testing, and documentation over infrastructure complexity. Since the project already uses SQLAlchemy and a centralized database configuration, migrating to PostgreSQL later would be straightforward if production requirements demanded it.

### Integer IDs Instead of UUIDs

The API uses auto-increment integer IDs.

Reasoning:

- simpler models and foreign keys
- easier manual testing in Swagger/Postman
- easier explanation during the interview
- enough for a single-service case with no distributed ID generation needs

## Architecture

The project follows a layered architecture:

`Router -> Service -> Repository -> Model`

### Responsibilities

- Router: handles HTTP input/output and dependency injection
- Service: applies business rules and use-case logic
- Repository: centralizes database access
- Model: defines persistence structure
- Schema: defines API contracts separately from ORM models

### Patterns Used

- Repository Pattern
- DTO Pattern with Pydantic schemas
- Dependency Injection with FastAPI `Depends`

## Project Structure

```text
digital-lib/
├── app/
│   ├── config.py
│   ├── database.py
│   ├── exceptions.py
│   ├── logging_config.py
│   ├── main.py
│   ├── models/
│   ├── repositories/
│   ├── routers/
│   ├── schemas/
│   └── services/
├── main.py
├── pyproject.toml
├── tests/
├── uv.lock
└── README.md
```

## Entities

### User

- `id`
- `name`
- `email`
- `is_active`
- `created_at`
- `updated_at`

### Book

- `id`
- `title`
- `author`
- `isbn`
- `published_year`
- `total_copies`
- `available_copies`
- `created_at`
- `updated_at`

### Loan

- `id`
- `user_id`
- `book_id`
- `loan_date`
- `due_date`
- `return_date`
- `fine_amount`
- `status`
- `created_at`

## Main Business Rules

- Standard loan period: 14 days
- Fine: R$ 2.00 per overdue day
- A user can have at most 3 open loans
- Overdue loans still count toward the user loan limit
- A book must have available copies to be borrowed
- Returning a book restores availability
- A loan can be renewed once while still active
- Returned loans cannot be renewed
- Overdue loans cannot be renewed
- Renewal extends the current due date by 14 days
- `available_copies` cannot be greater than `total_copies`
- ISBN is optional, but unique when provided

## Key Design Decisions

### Loan as a First-Class Entity

Loan was modeled as its own entity instead of a simple user-book association because the relationship has its own lifecycle and business meaning:

- due date
- return date
- fine
- status
- history

### Loan Statuses

The chosen statuses are:

- `ACTIVE`
- `OVERDUE`
- `RETURNED`

This is the minimum useful set needed to represent the loan lifecycle required by the case.

### Author as a String

The case only required three mandatory entities: User, Book, and Loan. Because of that, `author` was modeled as a string inside `Book` instead of introducing a separate `Author` entity early.

### API Schemas Separate from ORM Models

The API does not expose SQLAlchemy models directly. Pydantic schemas are used for:

- create input
- update input
- response output

This keeps persistence concerns separate from the public API contract.

## Implemented Features

### Users

- List users
- Create user
- Get user by ID
- List loans associated with a user

### Books

- List books
- Create book
- Get book by ID
- Check availability

### Loans

- Create loan
- Renew loan
- Return loan
- List all loans
- List active loans
- List overdue loans
- List loan history by user

### API Quality

- Swagger/OpenAPI docs available automatically
- Global exception handlers
- Validation with Pydantic
- Pagination on list endpoints
- Structured request logging via middleware
- Structured business event logging in the service layer
- Automated unit and integration tests with pytest
- Rate limiting on state-changing endpoints

## Installation

### Requirements

- Python 3.11+
- `uv` installed

### Install dependencies

```bash
uv sync
```

## Running the Application

```bash
uv run python main.py
```

Application URLs:

- API: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`
- Health check: `http://127.0.0.1:8000/health`

## Example API Usage

### Create a user

`POST /users`

```json
{
  "name": "Felipe Silva",
  "email": "felipe@example.com"
}
```

### Create a book

`POST /books`

```json
{
  "title": "Clean Architecture",
  "author": "Robert C. Martin",
  "isbn": "9780134494166",
  "published_year": 2017,
  "total_copies": 3,
  "available_copies": 3
}
```

### Create a loan

`POST /loans`

```json
{
  "user_id": 1,
  "book_id": 1
}
```

### Return a loan

`POST /loans/1/return`

No request body required.

### Renew a loan

`POST /loans/1/renew`

No request body required.

### Paginated list example

`GET /books?skip=0&limit=10`

Response shape:

```json
{
  "total": 1,
  "skip": 0,
  "limit": 10,
  "items": [
    {
      "id": 1,
      "title": "Clean Architecture",
      "author": "Robert C. Martin",
      "isbn": "9780134494166",
      "published_year": 2017,
      "total_copies": 3,
      "available_copies": 3,
      "created_at": "2026-03-07T10:00:00",
      "updated_at": "2026-03-07T10:00:00"
    }
  ]
}
```

## Logging

The application currently uses structured JSON logs.

Two logging layers are implemented:

- HTTP request logging in middleware
- business event logging in the service layer

Examples of logged events:

- `http_request`
- `user_created`
- `book_created`
- `loan_created`
- `loan_renewed`
- `loan_returned`
- `loan_overdue`

This helps with debugging, traceability, and future observability improvements.

## Rate Limiting

The API currently applies rate limiting to state-changing endpoints using `slowapi`.

Initial protection was added to write operations such as:

- `POST /users`
- `POST /books`
- `POST /loans`
- `POST /loans/{loan_id}/renew`
- `POST /loans/{loan_id}/return`

This was a deliberate choice to protect the endpoints that create or change system state while keeping read endpoints unrestricted for evaluation usability.

## Testing

The project currently includes automated tests using:

- `pytest`
- `FastAPI TestClient`
- a dedicated SQLite test database per test run
- isolated service tests with mocked repositories

The current suite includes:

- integration tests for API endpoints and end-to-end flows
- unit tests for service-layer business rules

Current coverage includes:

- health check
- user creation and conflict handling
- user pagination
- input normalization checks
- book creation and availability
- ISBN conflict handling
- inventory rule validation
- loan creation and return flow
- loan renewal flow
- loan renewal limit rule
- returned loan renewal rejection
- maximum active loan rule
- unavailable book rule
- loan pagination and user loan history pagination
- isolated service-level rule validation with mocks

### Run tests

```bash
uv run pytest
```

## Error Handling

The API currently maps domain exceptions to HTTP responses:

- `404 Not Found`: resource does not exist
- `409 Conflict`: duplicate or conflicting resource state
- `400 Bad Request`: violated business rule

Examples:

- creating a user with an email that already exists
- borrowing a book with no available copies
- returning an already returned loan

## Notes

- Date/time handling is currently kept simple for the SQLite-based version of the project
- Schema changes currently require recreating the local SQLite database because the project uses metadata creation instead of migrations
- Transaction handling is currently repository-commit based for clarity; a future hardening step would move multi-entity transaction control into the service layer
- Docker and Postman export are planned as next steps
