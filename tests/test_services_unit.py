from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.exceptions import BusinessRuleError, ConflictError
from app.models.loan import LoanStatus
from app.schemas.book import BookCreate
from app.schemas.loan import LoanCreate
from app.schemas.user import UserCreate
from app.services.book import BookService
from app.services.loan import LoanService
from app.services.user import UserService


def test_user_service_create_user_raises_conflict_for_duplicate_email() -> None:
    repository = Mock()
    repository.get_by_email.return_value = SimpleNamespace(id=1, email="felipe@example.com")

    service = UserService(repository)

    payload = UserCreate(
        name="Felipe Silva",
        email="felipe@example.com",
    )

    with pytest.raises(ConflictError, match="A user with this email already exists"):
        service.create_user(payload)

    repository.create.assert_not_called()


def test_book_service_create_book_raises_business_rule_for_invalid_inventory() -> None:
    repository = Mock()
    repository.get_by_isbn.return_value = None

    service = BookService(repository)

    payload = BookCreate(
        title="Clean Architecture",
        author="Robert C. Martin",
        isbn="9780134494166",
        published_year=2017,
        total_copies=1,
        available_copies=2,
    )

    with pytest.raises(BusinessRuleError, match="Available copies cannot be greater than total copies"):
        service.create_book(payload)

    repository.create.assert_not_called()


def test_loan_service_create_loan_raises_when_user_reaches_limit() -> None:
    loan_repository = Mock()
    user_repository = Mock()
    book_repository = Mock()
    reservation_service = Mock()

    user = SimpleNamespace(id=1)
    book = SimpleNamespace(id=1, available_copies=1)

    user_repository.get_by_id.return_value = user
    book_repository.get_by_id.return_value = book
    loan_repository.count_active_by_user.return_value = 3

    service = LoanService(
        loan_repository=loan_repository,
        user_repository=user_repository,
        book_repository=book_repository,
        reservation_service=reservation_service,
    )

    payload = LoanCreate(user_id=1, book_id=1)

    with pytest.raises(BusinessRuleError, match="User has reached the maximum number of active loans"):
        service.create_loan(payload)

    loan_repository.create.assert_not_called()
    book_repository.update.assert_not_called()


def test_loan_service_create_loan_raises_when_book_is_unavailable() -> None:
    loan_repository = Mock()
    user_repository = Mock()
    book_repository = Mock()
    reservation_service = Mock()

    user = SimpleNamespace(id=1)
    book = SimpleNamespace(id=1, available_copies=0)

    user_repository.get_by_id.return_value = user
    book_repository.get_by_id.return_value = book
    loan_repository.count_active_by_user.return_value = 0

    service = LoanService(
        loan_repository=loan_repository,
        user_repository=user_repository,
        book_repository=book_repository,
        reservation_service=reservation_service,
    )

    payload = LoanCreate(user_id=1, book_id=1)

    with pytest.raises(BusinessRuleError, match="Book is not available for loan"):
        service.create_loan(payload)

    loan_repository.create.assert_not_called()
    book_repository.update.assert_not_called()


def test_loan_service_return_loan_calculates_fine_and_marks_returned() -> None:
    loan_repository = Mock()
    user_repository = Mock()
    book_repository = Mock()
    reservation_service = Mock()

    loan = SimpleNamespace(
        id=1,
        user_id=1,
        book_id=1,
        status=LoanStatus.ACTIVE.value,
        due_date=datetime(2026, 3, 1, 10, 0, 0),
    )
    book = SimpleNamespace(
        id=1,
        available_copies=0,
        total_copies=1,
    )

    loan_repository.list_active.return_value = []
    loan_repository.get_by_id.return_value = loan
    loan_repository.update.return_value = SimpleNamespace(
        id=1,
        user_id=1,
        book_id=1,
        status=LoanStatus.RETURNED.value,
        fine_amount=Decimal("4.00"),
        return_date=datetime(2026, 3, 3, 10, 0, 0),
    )
    book_repository.get_by_id.return_value = book

    service = LoanService(
        loan_repository=loan_repository,
        user_repository=user_repository,
        book_repository=book_repository,
        reservation_service=reservation_service,
    )

    service._utc_now = Mock(return_value=datetime(2026, 3, 3, 10, 0, 0))

    result = service.return_loan(1)

    assert result.status == LoanStatus.RETURNED.value
    assert result.fine_amount == Decimal("4.00")

    book_repository.update.assert_called_once_with(
        book,
        available_copies=1,
    )
    loan_repository.update.assert_called_once_with(
        loan,
        return_date=datetime(2026, 3, 3, 10, 0, 0),
        fine_amount=Decimal("4.00"),
        status=LoanStatus.RETURNED.value,
    )

    reservation_service.promote_next_waiting_reservation.assert_called_once_with(book.id)


def test_loan_service_renew_loan_increases_due_date_and_renewal_count() -> None:
    loan_repository = Mock()
    user_repository = Mock()
    book_repository = Mock()
    reservation_service = Mock()

    loan = SimpleNamespace(
        id=1,
        user_id=1,
        book_id=1,
        status=LoanStatus.ACTIVE.value,
        due_date=datetime(2026, 3, 10, 10, 0, 0),
        renewal_count=0,
    )

    updated_loan = SimpleNamespace(
        id=1,
        user_id=1,
        book_id=1,
        status=LoanStatus.ACTIVE.value,
        due_date=datetime(2026, 3, 24, 10, 0, 0),
        renewal_count=1,
    )

    loan_repository.list_active.return_value = []
    loan_repository.get_by_id.return_value = loan
    loan_repository.update.return_value = updated_loan

    service = LoanService(
        loan_repository=loan_repository,
        user_repository=user_repository,
        book_repository=book_repository,
        reservation_service=reservation_service,
    )

    result = service.renew_loan(1)

    assert result.renewal_count == 1
    assert result.due_date == datetime(2026, 3, 24, 10, 0, 0)

    loan_repository.update.assert_called_once_with(
        loan,
        due_date=datetime(2026, 3, 24, 10, 0, 0),
        renewal_count=1,
    )


def test_loan_service_renew_loan_raises_when_limit_reached() -> None:
    loan_repository = Mock()
    user_repository = Mock()
    book_repository = Mock()
    reservation_service = Mock()

    loan = SimpleNamespace(
        id=1,
        user_id=1,
        book_id=1,
        status=LoanStatus.ACTIVE.value,
        due_date=datetime(2026, 3, 10, 10, 0, 0),
        renewal_count=1,
    )

    loan_repository.list_active.return_value = []
    loan_repository.get_by_id.return_value = loan

    service = LoanService(
        loan_repository=loan_repository,
        user_repository=user_repository,
        book_repository=book_repository,
        reservation_service=reservation_service,
    )

    with pytest.raises(BusinessRuleError, match="Loan renewal limit reached"):
        service.renew_loan(1)

    loan_repository.update.assert_not_called()