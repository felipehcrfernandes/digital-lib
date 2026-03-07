from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.loan import Loan, LoanStatus


class LoanRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(self, *, skip: int = 0, limit: int = 10) -> list[Loan]:
        statement = select(Loan).order_by(Loan.id).offset(skip).limit(limit)
        return list(self.db.scalars(statement).all())

    def count_all(self) -> int:
        statement = select(func.count()).select_from(Loan)
        return self.db.scalar(statement) or 0

    def get_by_id(self, loan_id: int) -> Loan | None:
        return self.db.get(Loan, loan_id)

    def list_active(self, *, skip: int = 0, limit: int = 10) -> list[Loan]:
        statement = (
            select(Loan)
            .where(Loan.status == LoanStatus.ACTIVE.value)
            .order_by(Loan.id)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(statement).all())

    def count_active(self) -> int:
        statement = select(func.count()).select_from(Loan).where(Loan.status == LoanStatus.ACTIVE.value)
        return self.db.scalar(statement) or 0

    def list_overdue(self, *, skip: int = 0, limit: int = 10) -> list[Loan]:
        statement = (
            select(Loan)
            .where(Loan.status == LoanStatus.OVERDUE.value)
            .order_by(Loan.id)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(statement).all())

    def count_overdue(self) -> int:
        statement = select(func.count()).select_from(Loan).where(Loan.status == LoanStatus.OVERDUE.value)
        return self.db.scalar(statement) or 0

    def list_by_user(self, user_id: int, *, skip: int = 0, limit: int = 10) -> list[Loan]:
        statement = (
            select(Loan)
            .where(Loan.user_id == user_id)
            .order_by(Loan.id)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(statement).all())

    def count_by_user(self, user_id: int) -> int:
        statement = select(func.count()).select_from(Loan).where(Loan.user_id == user_id)
        return self.db.scalar(statement) or 0

    def count_active_by_user(self, user_id: int) -> int:
        statement = select(func.count()).select_from(Loan).where(
            Loan.user_id == user_id,
            Loan.status.in_([LoanStatus.ACTIVE.value, LoanStatus.OVERDUE.value]),
        )
        return self.db.scalar(statement) or 0

    def create(
        self,
        *,
        user_id: int,
        book_id: int,
        due_date: datetime,
        status: str,
    ) -> Loan:
        loan = Loan(
            user_id=user_id,
            book_id=book_id,
            due_date=due_date,
            status=status,
        )
        self.db.add(loan)
        self.db.commit()
        self.db.refresh(loan)
        return loan

    def update(self, loan: Loan, **changes: object) -> Loan:
        for field, value in changes.items():
            setattr(loan, field, value)

        self.db.add(loan)
        self.db.commit()
        self.db.refresh(loan)
        return loan