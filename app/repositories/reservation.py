from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.reservation import Reservation, ReservationStatus


class ReservationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(self, *, skip: int = 0, limit: int = 10) -> list[Reservation]:
        statement = select(Reservation).order_by(Reservation.id).offset(skip).limit(limit)
        return list(self.db.scalars(statement).all())

    def count_all(self) -> int:
        statement = select(func.count()).select_from(Reservation)
        return self.db.scalar(statement) or 0

    def get_by_id(self, reservation_id: int) -> Reservation | None:
        return self.db.get(Reservation, reservation_id)

    def list_by_user(self, user_id: int, *, skip: int = 0, limit: int = 10) -> list[Reservation]:
        statement = (
            select(Reservation)
            .where(Reservation.user_id == user_id)
            .order_by(Reservation.id)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(statement).all())

    def count_by_user(self, user_id: int) -> int:
        statement = select(func.count()).select_from(Reservation).where(Reservation.user_id == user_id)
        return self.db.scalar(statement) or 0

    def list_waiting_by_book(self, book_id: int, *, skip: int = 0, limit: int = 10) -> list[Reservation]:
        statement = (
            select(Reservation)
            .where(
                Reservation.book_id == book_id,
                Reservation.status == ReservationStatus.WAITING.value,
            )
            .order_by(Reservation.created_at, Reservation.id)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(statement).all())

    def count_waiting_by_book(self, book_id: int) -> int:
        statement = select(func.count()).select_from(Reservation).where(
            Reservation.book_id == book_id,
            Reservation.status == ReservationStatus.WAITING.value,
        )
        return self.db.scalar(statement) or 0

    def get_waiting_by_user_and_book(self, user_id: int, book_id: int) -> Reservation | None:
        statement = select(Reservation).where(
            Reservation.user_id == user_id,
            Reservation.book_id == book_id,
            Reservation.status == ReservationStatus.WAITING.value,
        )
        return self.db.scalar(statement)

    def get_ready_for_pickup_by_book(self, book_id: int) -> Reservation | None:
        statement = (
            select(Reservation)
            .where(
                Reservation.book_id == book_id,
                Reservation.status == ReservationStatus.READY_FOR_PICKUP.value,
            )
            .order_by(Reservation.available_at, Reservation.id)
            .limit(1)
        )
        return self.db.scalar(statement)

    def get_next_waiting_for_book(self, book_id: int) -> Reservation | None:
        statement = (
            select(Reservation)
            .where(
                Reservation.book_id == book_id,
                Reservation.status == ReservationStatus.WAITING.value,
            )
            .order_by(Reservation.created_at, Reservation.id)
            .limit(1)
        )
        return self.db.scalar(statement)

    def list_expired_ready_for_pickup(self, now: datetime) -> list[Reservation]:
        statement = (
            select(Reservation)
            .where(
                Reservation.status == ReservationStatus.READY_FOR_PICKUP.value,
                Reservation.expires_at.is_not(None),
                Reservation.expires_at < now,
            )
            .order_by(Reservation.expires_at, Reservation.id)
        )
        return list(self.db.scalars(statement).all())

    def create(self, *, user_id: int, book_id: int, status: str) -> Reservation:
        reservation = Reservation(
            user_id=user_id,
            book_id=book_id,
            status=status,
        )
        self.db.add(reservation)
        self.db.commit()
        self.db.refresh(reservation)
        return reservation

    def update(self, reservation: Reservation, **changes: object) -> Reservation:
        for field, value in changes.items():
            setattr(reservation, field, value)

        self.db.add(reservation)
        self.db.commit()
        self.db.refresh(reservation)
        return reservation