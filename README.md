# Digital Library API

REST API for managing a digital library, including users, books, and loans.

This project was built as a technical case focused on software architecture, design patterns, business rules, validation, and API quality in Python.

## Current Status

Implemented so far:

- User management
- Book catalog management
- Loan creation and return flow
- Loan renewal flow
- Book reservation flow
- Richer health endpoint with database check and lightweight metrics
- Simple LLM-powered chat assistant UI for library operations
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

- Docker setup
- Final delivery polish

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

This was a deliberate choice for the case: it keeps the project easy to run while preserving a production-conscious design through SQLAlchemy and centralized configuration. The priority was business completeness, testing, and documentation over infrastructure complexity. Since the project already uses SQLAlchemy and a centralized database configuration, migrating to PostgreSQL later would be straightforward if production requirements demanded it.

### Integer IDs Instead of UUIDs

The API uses auto-increment integer IDs.

Reasoning:

- simpler models and foreign keys
- easier manual testing in Swagger/Postman
- easier explanation of data relationships and examples
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
│   ├── llm/
│   ├── logging_config.py
│   ├── main.py
│   ├── models/
│   ├── repositories/
│   ├── routers/
│   ├── schemas/
│   ├── static/
│   └── services/
├── LLM-DETAILS.md
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
- `renewal_count`
- `created_at`

### Reservation

- `id`
- `user_id`
- `book_id`
- `status`
- `created_at`
- `available_at`
- `expires_at`
- `fulfilled_at`
- `cancelled_at`
- `expired_at`

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
- Reservations can only be created when a book has no available copies
- A user cannot keep more than one active reservation for the same book
- Reservation queue order is based on `created_at`, with `id` as a deterministic tie-breaker
- When a copy becomes available, the next reservation is promoted to `READY_FOR_PICKUP`
- A promoted reservation has a pickup window of 2 days
- Cancelling or expiring a `READY_FOR_PICKUP` reservation promotes the next waiting reservation automatically
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

### Reservation as a First-Class Entity

Reservation was modeled as its own entity because waiting for a book has its own lifecycle and business rules, separate from both catalog management and loans.

Key states:

- `WAITING`
- `READY_FOR_PICKUP`
- `FULFILLED`
- `CANCELLED`
- `EXPIRED`

This made it possible to represent queue position, temporary pickup priority, explicit expiration, and clean automatic promotion of the next user in line.

### Reservation Promotion in the Service Layer

Queue promotion is handled in the service layer rather than in the router or repository.

- the router only exposes reservation actions
- the repository only queries and persists reservation data
- the service decides when a reservation becomes `READY_FOR_PICKUP`, expires, or promotes the next user

This keeps the reservation workflow as domain logic instead of treating it as a manual operational concern.

### Reservation Design Rationale

The reservation feature intentionally adds more domain structure than a simple waiting list because availability alone is not enough to model the full user experience.

- `Reservation` is separate from `Loan` because waiting for a copy and borrowing a copy are different business events
- queue position is derived from `created_at` and `id` instead of being stored explicitly, which avoids redundant mutable state
- `READY_FOR_PICKUP` exists to model temporary priority after a copy becomes available
- the 2-day pickup window prevents a reservation from blocking inventory indefinitely
- automatic promotion after return, cancellation, or expiration keeps the queue fair without relying on manual intervention

This design keeps the workflow easy to explain in a review while still showing production-minded reasoning around lifecycle, fairness, and state transitions.

### Author as a String

The case only required three mandatory entities: User, Book, and Loan. Because of that, `author` was modeled as a string inside `Book` instead of introducing a separate `Author` entity early.

### API Schemas Separate from ORM Models

The API does not expose SQLAlchemy models directly. Pydantic schemas are used for:

- create input
- update input
- response output

This keeps persistence concerns separate from the public API contract.

### Update Capability Kept Internal First

Update capability was implemented in the repository and service layers for users and books to keep the modules extensible, but update endpoints were not exposed immediately in the HTTP layer.

This was a deliberate scope decision: the internal layers were prepared for future evolution without expanding the public API surface beyond the flows prioritized for the case.

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

### Reservations

- Create reservation for an unavailable book
- Get reservation by ID
- List all reservations
- List reservations by user
- List waiting reservations for a book
- Cancel reservation
- Fulfill reservation
- Automatic queue promotion after loan return
- Automatic queue promotion after reservation cancellation
- Automatic queue promotion after reservation expiration

### API Quality

- Swagger/OpenAPI docs available automatically
- Richer health endpoint with database check and lightweight metrics
- Global exception handlers
- Validation with Pydantic
- Pagination on list endpoints
- Structured request logging via middleware
- Structured business event logging in the service layer
- Automated unit and integration tests with pytest
- Rate limiting on state-changing endpoints

### Chat Assistant

- Simple browser chat UI served by FastAPI at `GET /chat/ui`
- Additive chat endpoint at `POST /chat`
- OpenAI-compatible provider integration via environment variables
- Server-side tool execution mapped to the existing service layer
- UX adapted for a non-technical operator using Brazilian Portuguese
- Security-oriented bounded tool set and environment-based provider configuration

## Installation

### Requirements

- Python 3.11+
- `uv` installed for the primary setup flow

Optional for chat usage:

- an OpenAI-compatible API key

### Dependency Source Of Truth

The project is primarily managed with `pyproject.toml` and `uv.lock`.

`requirements.txt` is included only as a compatibility helper for users who prefer plain `pip`. It should be treated as a convenience export, not as the main dependency definition.

### Install dependencies

Primary setup with `uv`:

```bash
uv sync
```

Alternative setup with `pip`:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Optional chat configuration

The REST API works without any LLM configuration.

The chat assistant requires a root `.env` file with values like:

```env
LLM_ENABLED=true
LLM_API_KEY=your_api_key
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1
LLM_TIMEOUT_SECONDS=30
```

If `LLM_ENABLED` is false or the provider is not configured correctly, the core API still runs normally and the chat feature degrades gracefully.

## Running the Application

With `uv`:

```bash
uv run python main.py
```

With a `pip`-based virtual environment:

```bash
python main.py
```

Application URLs:

- API: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`
- Health check: `http://127.0.0.1:8000/health`
- Chat UI: `http://127.0.0.1:8000/chat/ui`

### Run without chat

If you only want to review the API:

1. Install dependencies
2. Start the application
3. Open `http://127.0.0.1:8000/docs`

No LLM configuration is required for this flow.

### Run with chat

If you want to review the LLM assistant too:

1. Install dependencies
2. Create the root `.env` file with the LLM variables
3. Start the application
4. Open `http://127.0.0.1:8000/chat/ui`

This keeps the main backend usage path simple while still allowing the chat assistant to be enabled when needed.

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

### Create a reservation

`POST /reservations`

```json
{
  "user_id": 2,
  "book_id": 1
}
```

Reservations are only allowed when the book has no available copies.

When the book becomes available again, the first waiting reservation is promoted automatically to `READY_FOR_PICKUP` for 2 days.

### Get a reservation

`GET /reservations/1`

Example response after automatic promotion:

```json
{
  "id": 1,
  "user_id": 2,
  "book_id": 1,
  "status": "READY_FOR_PICKUP",
  "created_at": "2026-03-08T10:00:00",
  "available_at": "2026-03-10T09:30:00",
  "expires_at": "2026-03-12T09:30:00",
  "fulfilled_at": null,
  "cancelled_at": null,
  "expired_at": null
}
```

### List reservations by user

`GET /reservations/users/2?skip=0&limit=10`

This returns the standard paginated response structure used across all list endpoints.

### Cancel a reservation

`POST /reservations/1/cancel`

No request body required. Cancelling a reservation that is already `READY_FOR_PICKUP` automatically promotes the next waiting reservation, if one exists.

### Fulfill a reservation

`POST /reservations/1/fulfill`

No request body required. This is intended for reservations currently in `READY_FOR_PICKUP`.

### Health check

`GET /health`

Example response:

```json
{
  "status": "ok",
  "app_name": "Digital Library API",
  "version": "0.1.0",
  "timestamp": "2026-03-08T16:00:00+00:00",
  "database": {
    "status": "ok"
  },
  "metrics": {
    "users": 2,
    "books": 1,
    "loans_total": 1,
    "loans_active": 0,
    "loans_overdue": 0,
    "reservations_total": 1,
    "reservations_waiting": 0,
    "reservations_ready_for_pickup": 1
  }
}
```

The endpoint is intentionally simple: it confirms database connectivity and exposes a small set of business-relevant counters without introducing external monitoring infrastructure.

### Chat assistant

`POST /chat`

`GET /chat/ui`

The browser chat interface is the simplest way to use the assistant in the application.

The backend endpoint remains available for direct testing and integration.

Example request:

```json
{
  "message": "Create a user named Ana with email ana@example.com",
  "history": []
}
```

Example response shape:

```json
{
  "reply": "I created Ana successfully and she is now available in the library system.",
  "action": {
    "tool_name": "create_user",
    "success": true,
    "data": {
      "id": 1,
      "name": "Ana",
      "email": "ana@example.com",
      "is_active": true,
      "created_at": "2026-03-08T18:00:00",
      "updated_at": "2026-03-08T18:00:00"
    },
    "error": null
  }
}
```

The chat assistant is intentionally additive. It does not replace the existing REST API and does not bypass business rules. When the model chooses a tool, the server executes the corresponding existing service-layer operation, so validations and constraints stay centralized in the same backend logic as the normal endpoints.

For a deeper explanation of the architecture, tool design, security decisions, and future improvements, see [`LLM-DETAILS.md`](LLM-DETAILS.md).

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
- `reservation_created`
- `reservation_ready_for_pickup`
- `reservation_cancelled`
- `reservation_fulfilled`
- `reservation_expired`

This helps with debugging, traceability, and future observability improvements.

## Rate Limiting

The API currently applies rate limiting to state-changing endpoints using `slowapi`.

Initial protection was added to write operations such as:

- `POST /users`
- `POST /books`
- `POST /loans`
- `POST /loans/{loan_id}/renew`
- `POST /loans/{loan_id}/return`
- `POST /reservations`
- `POST /reservations/{reservation_id}/cancel`
- `POST /reservations/{reservation_id}/fulfill`
- `POST /chat`

This was a deliberate choice to protect the endpoints that create or change system state while keeping read endpoints unrestricted initially for simplicity and usability.

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
- reservation creation for unavailable books
- duplicate reservation prevention
- automatic promotion to `READY_FOR_PICKUP` after book return
- automatic promotion after cancelling a ready reservation
- reservation pagination by user
- loan pagination and user loan history pagination
- isolated service-level rule validation with mocks
- a Postman collection covering the main endpoints, main happy paths, and selected business-rule failures, without trying to mirror every implemented endpoint

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
- During development, schema changes may require recreating the local SQLite database because the project uses metadata creation instead of migrations
- In a production-ready environment, schema evolution should be handled with proper database migrations such as Alembic instead of deleting and recreating the database
- Transaction handling is currently repository-commit based for clarity; a future hardening step would move multi-entity transaction control into the service layer
- Docker is still a likely next step for easier environment setup
- Streaming chat responses, tighter response control, and richer UI polish are possible future improvements, but the current implementation intentionally stays simple to demonstrate the integration pattern clearly
