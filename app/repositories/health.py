from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.loan import Loan, LoanStatus
from app.models.reservation import Reservation, ReservationStatus
from app.models.user import User


class HealthRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def check_database(self) -> bool:
        result = self.db.execute(text("SELECT 1"))
        return result.scalar() == 1

    def count_users(self) -> int:
        statement = select(func.count()).select_from(User)
        return self.db.scalar(statement) or 0

    def count_books(self) -> int:
        statement = select(func.count()).select_from(Book)
        return self.db.scalar(statement) or 0

    def count_loans_total(self) -> int:
        statement = select(func.count()).select_from(Loan)
        return self.db.scalar(statement) or 0

    def count_loans_active(self) -> int:
        statement = select(func.count()).select_from(Loan).where(
            Loan.status == LoanStatus.ACTIVE.value
        )
        return self.db.scalar(statement) or 0

    def count_loans_overdue(self) -> int:
        statement = select(func.count()).select_from(Loan).where(
            Loan.status == LoanStatus.OVERDUE.value
        )
        return self.db.scalar(statement) or 0

    def count_reservations_total(self) -> int:
        statement = select(func.count()).select_from(Reservation)
        return self.db.scalar(statement) or 0

    def count_reservations_waiting(self) -> int:
        statement = select(func.count()).select_from(Reservation).where(
            Reservation.status == ReservationStatus.WAITING.value
        )
        return self.db.scalar(statement) or 0

    def count_reservations_ready_for_pickup(self) -> int:
        statement = select(func.count()).select_from(Reservation).where(
            Reservation.status == ReservationStatus.READY_FOR_PICKUP.value
        )
        return self.db.scalar(statement) or 0