from datetime import datetime
from app.models.loan import Loan, LoanStatus
from sqlalchemy import select
from sqlalchemy.orm import Session


class LoanRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(self) -> list[Loan]:
        statement = select(Loan).order_by(Loan.id)
        return list(self.db.scalars(statement).all())

    def get_by_id(self, loan_id: int) -> Loan | None:
        return self.db.get(Loan, loan_id)

    def list_active(self) -> list[Loan]:
        statement = select(Loan).where(Loan.status == LoanStatus.ACTIVE.value).order_by(Loan.id)
        return list(self.db.scalars(statement).all())

    def list_overdue(self) -> list[Loan]:
        statement = select(Loan).where(Loan.status == LoanStatus.OVERDUE.value).order_by(Loan.id)
        return list(self.db.scalars(statement).all())

    def list_by_user(self, user_id: int) -> list[Loan]:
        statement = select(Loan).where(Loan.user_id == user_id).order_by(Loan.id)
        return list(self.db.scalars(statement).all())

    def count_active_by_user(self, user_id: int) -> int:
        statement = select(Loan).where(
            Loan.user_id == user_id,
            Loan.status.in_([LoanStatus.ACTIVE.value, LoanStatus.OVERDUE.value]),
        )
        return len(list(self.db.scalars(statement).all()))

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