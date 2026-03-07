from fastapi import APIRouter, Depends, Query, Request, status
from app.limiter import limiter
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.book import BookRepository
from app.repositories.loan import LoanRepository
from app.repositories.user import UserRepository
from app.schemas.common import PaginatedResponse
from app.schemas.loan import LoanCreate, LoanResponse
from app.services.loan import LoanService

router = APIRouter(prefix="/loans", tags=["loans"])


def get_loan_service(db: Session = Depends(get_db)) -> LoanService:
    loan_repository = LoanRepository(db)
    user_repository = UserRepository(db)
    book_repository = BookRepository(db)
    return LoanService(
        loan_repository=loan_repository,
        user_repository=user_repository,
        book_repository=book_repository,
    )


@router.get("", response_model=PaginatedResponse[LoanResponse])
def list_loans(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    service: LoanService = Depends(get_loan_service),
) -> PaginatedResponse[LoanResponse]:
    return service.list_loans(skip=skip, limit=limit)


@router.get("/active", response_model=PaginatedResponse[LoanResponse])
def list_active_loans(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    service: LoanService = Depends(get_loan_service),
) -> PaginatedResponse[LoanResponse]:
    return service.list_active_loans(skip=skip, limit=limit)


@router.get("/overdue", response_model=PaginatedResponse[LoanResponse])
def list_overdue_loans(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    service: LoanService = Depends(get_loan_service),
) -> PaginatedResponse[LoanResponse]:
    return service.list_overdue_loans(skip=skip, limit=limit)


@router.post(
    "",
    response_model=LoanResponse,
    status_code=status.HTTP_201_CREATED,
)

@limiter.limit("20/minute")
def create_loan(
    request: Request,
    payload: LoanCreate,
    service: LoanService = Depends(get_loan_service),
) -> LoanResponse:
    return service.create_loan(payload)


@router.post("/{loan_id}/return", response_model=LoanResponse)
@limiter.limit("20/minute")
def return_loan(request: Request, loan_id: int, service: LoanService = Depends(get_loan_service)) -> LoanResponse:
    return service.return_loan(loan_id)