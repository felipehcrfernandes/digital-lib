from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserResponse
from app.services.user import UserService
from app.repositories.book import BookRepository
from app.repositories.loan import LoanRepository
from app.schemas.loan import LoanResponse
from app.services.loan import LoanService

router = APIRouter(prefix="/users", tags=["users"])


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    repository = UserRepository(db)
    return UserService(repository)

def get_loan_service(db: Session = Depends(get_db)) -> LoanService:
    loan_repository = LoanRepository(db)
    user_repository = UserRepository(db)
    book_repository = BookRepository(db)
    return LoanService(
        loan_repository=loan_repository,
        user_repository=user_repository,
        book_repository=book_repository,
    )


@router.get("", response_model=list[UserResponse])
def list_users(service: UserService = Depends(get_user_service)) -> list[UserResponse]:
    return service.list_users()


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, service: UserService = Depends(get_user_service)) -> UserResponse:
    return service.get_user(user_id)


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    payload: UserCreate,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    return service.create_user(payload)


@router.get("/{user_id}/loans", response_model=list[LoanResponse])
def list_user_loans(user_id: int, 
                    service: LoanService = Depends(get_loan_service),
) -> list[LoanResponse]:
    return service.list_user_loans(user_id)

