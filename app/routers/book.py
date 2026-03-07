from fastapi import APIRouter, Depends, Query, Request, status
from app.limiter import limiter
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.book import BookRepository
from app.schemas.book import BookCreate, BookResponse
from app.schemas.common import PaginatedResponse
from app.services.book import BookService

router = APIRouter(prefix="/books", tags=["books"])


def get_book_service(db: Session = Depends(get_db)) -> BookService:
    repository = BookRepository(db)
    return BookService(repository)


@router.get("", response_model=PaginatedResponse[BookResponse])
def list_books(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    service: BookService = Depends(get_book_service),
) -> PaginatedResponse[BookResponse]:
    return service.list_books(skip=skip, limit=limit)


@router.get("/{book_id}", response_model=BookResponse)
def get_book(book_id: int, service: BookService = Depends(get_book_service)) -> BookResponse:
    return service.get_book(book_id)


@router.post(
    "",
    response_model=BookResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
def create_book(
    request: Request, 
    payload: BookCreate,
    service: BookService = Depends(get_book_service),
) -> BookResponse:
    return service.create_book(payload)


@router.get("/{book_id}/availability", response_model=dict[str, int | bool])
def check_availability(
    book_id: int,
    service: BookService = Depends(get_book_service),
) -> dict[str, int | bool]:
    return service.check_availability(book_id)