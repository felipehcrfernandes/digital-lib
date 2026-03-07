from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.book import BookRepository
from app.repositories.loan import LoanRepository
from app.repositories.user import UserRepository
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


@router.get("", response_model=list[LoanResponse])
def list_loans(service: LoanService = Depends(get_loan_service)) -> list[LoanResponse]:
    return service.list_loans()


@router.get("/active", response_model=list[LoanResponse])
def list_active_loans(service: LoanService = Depends(get_loan_service)) -> list[LoanResponse]:
    return service.list_active_loans()


@router.get("/overdue", response_model=list[LoanResponse])
def list_overdue_loans(service: LoanService = Depends(get_loan_service)) -> list[LoanResponse]:
    return service.list_overdue_loans()


@router.post(
    "",
    response_model=LoanResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_loan(
    payload: LoanCreate,
    service: LoanService = Depends(get_loan_service),
) -> LoanResponse:
    return service.create_loan(payload)


@router.post("/{loan_id}/return", response_model=LoanResponse)
def return_loan(loan_id: int, service: LoanService = Depends(get_loan_service)) -> LoanResponse:
    return service.return_loan(loan_id)