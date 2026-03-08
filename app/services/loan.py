import logging

from datetime import datetime, timedelta
from decimal import Decimal

from app.exceptions import BusinessRuleError, NotFoundError
from app.models.book import Book
from app.models.loan import Loan, LoanStatus
from app.models.user import User
from app.repositories.book import BookRepository
from app.repositories.loan import LoanRepository
from app.repositories.user import UserRepository
from app.schemas.loan import LoanCreate, LoanResponse
from app.schemas.common import PaginatedResponse
from app.services.reservation import ReservationService

logger = logging.getLogger(__name__)

class LoanService:
    LOAN_PERIOD_DAYS = 14
    FINE_PER_DAY = Decimal("2.00")
    MAX_ACTIVE_LOANS = 3
    MAX_RENEWALS = 1

    def __init__(
        self,
        loan_repository: LoanRepository,
        user_repository: UserRepository,
        book_repository: BookRepository,
        reservation_service: ReservationService,
    ) -> None:
        self.loan_repository = loan_repository
        self.user_repository = user_repository
        self.book_repository = book_repository
        self.reservation_service = reservation_service

    def list_loans(self, *, skip: int = 0, limit: int = 10) -> PaginatedResponse[LoanResponse]:
        self._refresh_overdue_loans()
        items = self.loan_repository.list_all(skip=skip, limit=limit)
        total = self.loan_repository.count_all()
        return PaginatedResponse[LoanResponse](
            total=total,
            skip=skip,
            limit=limit,
            items=items,
        )

    def list_active_loans(self, *, skip: int = 0, limit: int = 10) -> PaginatedResponse[LoanResponse]:
        self._refresh_overdue_loans()
        items = self.loan_repository.list_active(skip=skip, limit=limit)
        total = self.loan_repository.count_active()
        return PaginatedResponse[LoanResponse](
            total=total,
            skip=skip,
            limit=limit,
            items=items,
        )

    def list_overdue_loans(self, *, skip: int = 0, limit: int = 10) -> PaginatedResponse[LoanResponse]:
        self._refresh_overdue_loans()
        items = self.loan_repository.list_overdue(skip=skip, limit=limit)
        total = self.loan_repository.count_overdue()
        return PaginatedResponse[LoanResponse](
            total=total,
            skip=skip,
            limit=limit,
            items=items,
        )

    def list_user_loans(self, user_id: int, *, skip: int = 0, limit: int = 10) -> PaginatedResponse[LoanResponse]:
        self._get_user_or_raise(user_id)
        self._refresh_overdue_loans()
        items = self.loan_repository.list_by_user(user_id, skip=skip, limit=limit)
        total = self.loan_repository.count_by_user(user_id)
        return PaginatedResponse[LoanResponse](
            total=total,
            skip=skip,
            limit=limit,
            items=items,
        )

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

        logger.info(
            "loan created",
            extra={
                "event": "loan_created",
                "loan_id": loan.id,
                "user_id": user.id,
                "book_id": book.id,
            },
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

        updated_loan = self.loan_repository.update(
            loan,
            return_date=returned_at,
            fine_amount=fine_amount,
            status=LoanStatus.RETURNED.value,
        )

        promoted_reservation = self.reservation_service.promote_next_waiting_reservation(book.id)

        logger.info(
            "loan returned",
            extra={
                "event": "loan_returned",
                "loan_id": updated_loan.id,
                "user_id": updated_loan.user_id,
                "book_id": updated_loan.book_id,
                "fine_amount": updated_loan.fine_amount,
                "promoted_reservation_id": promoted_reservation.id if promoted_reservation else None,
            },
        )

        return updated_loan
    
    def renew_loan(self, loan_id: int) -> Loan:
        self._refresh_overdue_loans()

        loan = self.get_loan(loan_id)

        if loan.status == LoanStatus.RETURNED.value:
            raise BusinessRuleError("Returned loans cannot be renewed")

        if loan.status == LoanStatus.OVERDUE.value:
            raise BusinessRuleError("Overdue loans cannot be renewed")

        if loan.renewal_count >= self.MAX_RENEWALS:
            raise BusinessRuleError("Loan renewal limit reached")

        updated_loan = self.loan_repository.update(
            loan,
            due_date=loan.due_date + timedelta(days=self.LOAN_PERIOD_DAYS),
            renewal_count=loan.renewal_count + 1,
        )

        logger.info(
            "loan renewed",
            extra={
                "event": "loan_renewed",
                "loan_id": updated_loan.id,
                "user_id": updated_loan.user_id,
                "book_id": updated_loan.book_id,
            },
        )

        return updated_loan

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

                logger.info(
                    "loan marked as overdue",
                    extra={
                        "event": "loan_overdue",
                        "loan_id": loan.id,
                        "user_id": loan.user_id,
                        "book_id": loan.book_id,
                    },
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