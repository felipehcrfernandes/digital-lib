import logging
from datetime import datetime, timedelta

from app.exceptions import BusinessRuleError, NotFoundError
from app.models.book import Book
from app.models.reservation import Reservation, ReservationStatus
from app.models.user import User
from app.repositories.book import BookRepository
from app.repositories.reservation import ReservationRepository
from app.repositories.user import UserRepository
from app.schemas.common import PaginatedResponse
from app.schemas.reservation import ReservationCreate, ReservationResponse

logger = logging.getLogger(__name__)


class ReservationService:
    PICKUP_WINDOW_DAYS = 2

    def __init__(
        self,
        reservation_repository: ReservationRepository,
        user_repository: UserRepository,
        book_repository: BookRepository,
    ) -> None:
        self.reservation_repository = reservation_repository
        self.user_repository = user_repository
        self.book_repository = book_repository

    def list_reservations(self, *, skip: int = 0, limit: int = 10) -> PaginatedResponse[ReservationResponse]:
        self._refresh_expired_ready_for_pickup()
        items = self.reservation_repository.list_all(skip=skip, limit=limit)
        total = self.reservation_repository.count_all()
        return PaginatedResponse[ReservationResponse](
            total=total,
            skip=skip,
            limit=limit,
            items=items,
        )

    def list_user_reservations(
        self,
        user_id: int,
        *,
        skip: int = 0,
        limit: int = 10,
    ) -> PaginatedResponse[ReservationResponse]:
        self._refresh_expired_ready_for_pickup()
        self._get_user_or_raise(user_id)

        items = self.reservation_repository.list_by_user(user_id, skip=skip, limit=limit)
        total = self.reservation_repository.count_by_user(user_id)
        return PaginatedResponse[ReservationResponse](
            total=total,
            skip=skip,
            limit=limit,
            items=items,
        )

    def list_book_waiting_reservations(
        self,
        book_id: int,
        *,
        skip: int = 0,
        limit: int = 10,
    ) -> PaginatedResponse[ReservationResponse]:
        self._refresh_expired_ready_for_pickup()
        self._get_book_or_raise(book_id)

        items = self.reservation_repository.list_waiting_by_book(book_id, skip=skip, limit=limit)
        total = self.reservation_repository.count_waiting_by_book(book_id)
        return PaginatedResponse[ReservationResponse](
            total=total,
            skip=skip,
            limit=limit,
            items=items,
        )

    def create_reservation(self, payload: ReservationCreate) -> Reservation:
        self._refresh_expired_ready_for_pickup()

        user = self._get_user_or_raise(payload.user_id)
        book = self._get_book_or_raise(payload.book_id)

        if book.available_copies > 0:
            raise BusinessRuleError("Book is currently available and does not need a reservation")

        if self._user_has_active_reservation_for_book(user.id, book.id):
            raise BusinessRuleError("User already has an active reservation for this book")

        reservation = self.reservation_repository.create(
            user_id=user.id,
            book_id=book.id,
            status=ReservationStatus.WAITING.value,
        )

        logger.info(
            "reservation created",
            extra={
                "event": "reservation_created",
                "reservation_id": reservation.id,
                "user_id": reservation.user_id,
                "book_id": reservation.book_id,
            },
        )

        return reservation

    def cancel_reservation(self, reservation_id: int) -> Reservation:
        self._refresh_expired_ready_for_pickup()

        reservation = self.get_reservation(reservation_id)

        if reservation.status in {
            ReservationStatus.CANCELLED.value,
            ReservationStatus.EXPIRED.value,
            ReservationStatus.FULFILLED.value,
        }:
            raise BusinessRuleError("Reservation can no longer be cancelled")

        updated_reservation = self.reservation_repository.update(
            reservation,
            status=ReservationStatus.CANCELLED.value,
            cancelled_at=self._utc_now(),
        )

        logger.info(
            "reservation cancelled",
            extra={
                "event": "reservation_cancelled",
                "reservation_id": updated_reservation.id,
                "user_id": updated_reservation.user_id,
                "book_id": updated_reservation.book_id,
            },
        )

        if reservation.status == ReservationStatus.READY_FOR_PICKUP.value:
            self._promote_next_waiting_reservation(updated_reservation.book_id)

        return updated_reservation

    def fulfill_reservation(self, reservation_id: int) -> Reservation:
        self._refresh_expired_ready_for_pickup()

        reservation = self.get_reservation(reservation_id)

        if reservation.status != ReservationStatus.READY_FOR_PICKUP.value:
            raise BusinessRuleError("Only reservations ready for pickup can be fulfilled")

        updated_reservation = self.reservation_repository.update(
            reservation,
            status=ReservationStatus.FULFILLED.value,
            fulfilled_at=self._utc_now(),
        )

        logger.info(
            "reservation fulfilled",
            extra={
                "event": "reservation_fulfilled",
                "reservation_id": updated_reservation.id,
                "user_id": updated_reservation.user_id,
                "book_id": updated_reservation.book_id,
            },
        )

        return updated_reservation

    def promote_next_waiting_reservation(self, book_id: int) -> Reservation | None:
        self._refresh_expired_ready_for_pickup()
        return self._promote_next_waiting_reservation(book_id)

    def get_reservation(self, reservation_id: int) -> Reservation:
        reservation = self.reservation_repository.get_by_id(reservation_id)
        if reservation is None:
            raise NotFoundError("Reservation not found")
        return reservation

    def _promote_next_waiting_reservation(self, book_id: int) -> Reservation | None:
        book = self._get_book_or_raise(book_id)

        current_ready = self.reservation_repository.get_ready_for_pickup_by_book(book.id)
        if current_ready is not None:
            return current_ready

        if book.available_copies <= 0:
            return None

        next_reservation = self.reservation_repository.get_next_waiting_for_book(book.id)
        if next_reservation is None:
            return None

        now = self._utc_now()
        expires_at = now + timedelta(days=self.PICKUP_WINDOW_DAYS)

        updated_reservation = self.reservation_repository.update(
            next_reservation,
            status=ReservationStatus.READY_FOR_PICKUP.value,
            available_at=now,
            expires_at=expires_at,
        )

        logger.info(
            "reservation ready for pickup",
            extra={
                "event": "reservation_ready_for_pickup",
                "reservation_id": updated_reservation.id,
                "user_id": updated_reservation.user_id,
                "book_id": updated_reservation.book_id,
                "expires_at": updated_reservation.expires_at.isoformat(),
            },
        )

        return updated_reservation

    def _refresh_expired_ready_for_pickup(self) -> None:
        now = self._utc_now()
        expired_reservations = self.reservation_repository.list_expired_ready_for_pickup(now)

        for reservation in expired_reservations:
            updated_reservation = self.reservation_repository.update(
                reservation,
                status=ReservationStatus.EXPIRED.value,
                expired_at=now,
            )

            logger.info(
                "reservation expired",
                extra={
                    "event": "reservation_expired",
                    "reservation_id": updated_reservation.id,
                    "user_id": updated_reservation.user_id,
                    "book_id": updated_reservation.book_id,
                },
            )

            self._promote_next_waiting_reservation(updated_reservation.book_id)

    def _user_has_active_reservation_for_book(self, user_id: int, book_id: int) -> bool:
        waiting_reservation = self.reservation_repository.get_waiting_by_user_and_book(user_id, book_id)
        if waiting_reservation is not None:
            return True

        total_reservations = self.reservation_repository.count_by_user(user_id)
        if total_reservations == 0:
            return False

        user_reservations = self.reservation_repository.list_by_user(
            user_id,
            skip=0,
            limit=total_reservations,
        )

        return any(
            reservation.book_id == book_id
            and reservation.status == ReservationStatus.READY_FOR_PICKUP.value
            for reservation in user_reservations
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