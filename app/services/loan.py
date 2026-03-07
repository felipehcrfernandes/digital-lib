from datetime import datetime, timedelta
from decimal import Decimal

from app.exceptions import BusinessRuleError, NotFoundError
from app.models.book import Book
from app.models.loan import Loan, LoanStatus
from app.models.user import User
from app.repositories.book import BookRepository
from app.repositories.loan import LoanRepository
from app.repositories.user import UserRepository
from app.schemas.loan import LoanCreate


class LoanService:
    LOAN_PERIOD_DAYS = 14
    FINE_PER_DAY = Decimal("2.00")
    MAX_ACTIVE_LOANS = 3

    def __init__(
        self,
        loan_repository: LoanRepository,
        user_repository: UserRepository,
        book_repository: BookRepository,
    ) -> None:
        self.loan_repository = loan_repository
        self.user_repository = user_repository
        self.book_repository = book_repository

    def list_loans(self) -> list[Loan]:
        self._refresh_overdue_loans()
        return self.loan_repository.list_all()

    def list_active_loans(self) -> list[Loan]:
        self._refresh_overdue_loans()
        return self.loan_repository.list_active()

    def list_overdue_loans(self) -> list[Loan]:
        self._refresh_overdue_loans()
        return self.loan_repository.list_overdue()

    def list_user_loans(self, user_id: int) -> list[Loan]:
        self._get_user_or_raise(user_id)
        self._refresh_overdue_loans()
        return self.loan_repository.list_by_user(user_id)

    def create_loan(self, payload: LoanCreate) -> Loan:
        user = self._get_user_or_raise(payload.user_id)
        book = self._get_book_or_raise(payload.book_id)

        active_loans = self.loan_repository.count_active_by_user(user.id)
        if active_loans >= self.MAX_ACTIVE_LOANS:
            raise BusinessRuleError("User has reached the maximum number of active loans")

        if book.available_copies <= 0:
            raise BusinessRuleError("Book is not available for loan")

        due_date = self._utc_now() + timedelta(days=self.LOAN_PERIOD_DAYS)

        loan = self.loan_repository.create(
            user_id=user.id,
            book_id=book.id,
            due_date=due_date,
            status=LoanStatus.ACTIVE.value,
        )

        self.book_repository.update(
            book,
            available_copies=book.available_copies - 1,
        )

        return loan

    def return_loan(self, loan_id: int) -> Loan:
        self._refresh_overdue_loans()

        loan = self.get_loan(loan_id)
        if loan.status == LoanStatus.RETURNED.value:
            raise BusinessRuleError("Loan has already been returned")

        book = self._get_book_or_raise(loan.book_id)

        returned_at = self._utc_now()
        overdue_days = max(0, (returned_at.date() - loan.due_date.date()).days)
        fine_amount = Decimal(overdue_days) * self.FINE_PER_DAY

        if book.available_copies >= book.total_copies:
            raise BusinessRuleError("Book inventory is already at maximum capacity")

        self.book_repository.update(
            book,
            available_copies=book.available_copies + 1,
        )

        return self.loan_repository.update(
            loan,
            return_date=returned_at,
            fine_amount=fine_amount,
            status=LoanStatus.RETURNED.value,
        )

    def get_loan(self, loan_id: int) -> Loan:
        loan = self.loan_repository.get_by_id(loan_id)
        if loan is None:
            raise NotFoundError("Loan not found")
        return loan

    def _refresh_overdue_loans(self) -> None:
        now = self._utc_now()

        for loan in self.loan_repository.list_active():
            if loan.due_date < now:
                self.loan_repository.update(
                    loan,
                    status=LoanStatus.OVERDUE.value,
                )

    def _get_user_or_raise(self, user_id: int) -> User:
        user = self.user_repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return user

    def _get_book_or_raise(self, book_id: int) -> Book:
        book = self.book_repository.get_by_id(book_id)
        if book is None:
            raise NotFoundError("Book not found")
        return book

    def _utc_now(self) -> datetime:
        return datetime.utcnow()