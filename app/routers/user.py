from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.limiter import limiter
from app.repositories.book import BookRepository
from app.repositories.loan import LoanRepository
from app.repositories.reservation import ReservationRepository
from app.repositories.user import UserRepository
from app.schemas.common import PaginatedResponse
from app.schemas.loan import LoanResponse
from app.schemas.user import UserCreate, UserResponse
from app.services.loan import LoanService
from app.services.reservation import ReservationService
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["users"])


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    repository = UserRepository(db)
    return UserService(repository)


def get_loan_service(db: Session = Depends(get_db)) -> LoanService:
    loan_repository = LoanRepository(db)
    user_repository = UserRepository(db)
    book_repository = BookRepository(db)
    reservation_repository = ReservationRepository(db)

    reservation_service = ReservationService(
        reservation_repository=reservation_repository,
        user_repository=user_repository,
        book_repository=book_repository,
    )

    return LoanService(
        loan_repository=loan_repository,
        user_repository=user_repository,
        book_repository=book_repository,
        reservation_service=reservation_service,
    )


@router.get("", response_model=PaginatedResponse[UserResponse])
def list_users(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    service: UserService = Depends(get_user_service),
) -> PaginatedResponse[UserResponse]:
    return service.list_users(skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, service: UserService = Depends(get_user_service)) -> UserResponse:
    return service.get_user(user_id)


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
def create_user(
    request: Request,
    payload: UserCreate,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    return service.create_user(payload)


@router.get("/{user_id}/loans", response_model=PaginatedResponse[LoanResponse])
def list_user_loans(
    user_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    service: LoanService = Depends(get_loan_service),
) -> PaginatedResponse[LoanResponse]:
    return service.list_user_loans(user_id, skip=skip, limit=limit)