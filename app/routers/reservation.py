from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.limiter import limiter
from app.repositories.book import BookRepository
from app.repositories.reservation import ReservationRepository
from app.repositories.user import UserRepository
from app.schemas.common import PaginatedResponse
from app.schemas.reservation import ReservationCreate, ReservationResponse
from app.services.reservation import ReservationService

router = APIRouter(prefix="/reservations", tags=["reservations"])


def get_reservation_service(db: Session = Depends(get_db)) -> ReservationService:
    reservation_repository = ReservationRepository(db)
    user_repository = UserRepository(db)
    book_repository = BookRepository(db)
    return ReservationService(
        reservation_repository=reservation_repository,
        user_repository=user_repository,
        book_repository=book_repository,
    )


@router.get("", response_model=PaginatedResponse[ReservationResponse])
def list_reservations(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    service: ReservationService = Depends(get_reservation_service),
) -> PaginatedResponse[ReservationResponse]:
    return service.list_reservations(skip=skip, limit=limit)


@router.get("/{reservation_id}", response_model=ReservationResponse)
def get_reservation(
    reservation_id: int,
    service: ReservationService = Depends(get_reservation_service),
) -> ReservationResponse:
    return service.get_reservation(reservation_id)


@router.get("/users/{user_id}", response_model=PaginatedResponse[ReservationResponse])
def list_user_reservations(
    user_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    service: ReservationService = Depends(get_reservation_service),
) -> PaginatedResponse[ReservationResponse]:
    return service.list_user_reservations(user_id, skip=skip, limit=limit)


@router.get("/books/{book_id}/waiting", response_model=PaginatedResponse[ReservationResponse])
def list_book_waiting_reservations(
    book_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    service: ReservationService = Depends(get_reservation_service),
) -> PaginatedResponse[ReservationResponse]:
    return service.list_book_waiting_reservations(book_id, skip=skip, limit=limit)


@router.post(
    "",
    response_model=ReservationResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
def create_reservation(
    request: Request,
    payload: ReservationCreate,
    service: ReservationService = Depends(get_reservation_service),
) -> ReservationResponse:
    return service.create_reservation(payload)


@router.post("/{reservation_id}/cancel", response_model=ReservationResponse)
@limiter.limit("10/minute")
def cancel_reservation(
    request: Request,
    reservation_id: int,
    service: ReservationService = Depends(get_reservation_service),
) -> ReservationResponse:
    return service.cancel_reservation(reservation_id)


@router.post("/{reservation_id}/fulfill", response_model=ReservationResponse)
@limiter.limit("10/minute")
def fulfill_reservation(
    request: Request,
    reservation_id: int,
    service: ReservationService = Depends(get_reservation_service),
) -> ReservationResponse:
    return service.fulfill_reservation(reservation_id)