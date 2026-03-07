from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.book import BookRepository
from app.schemas.book import BookCreate, BookResponse
from app.services.book import BookService

router = APIRouter(prefix="/books", tags=["books"])


def get_book_service(db: Session = Depends(get_db)) -> BookService:
    repository = BookRepository(db)
    return BookService(repository)


@router.get("", response_model=list[BookResponse])
def list_books(service: BookService = Depends(get_book_service)) -> list[BookResponse]:
    return service.list_books()


@router.get("/{book_id}", response_model=BookResponse)
def get_book(book_id: int, service: BookService = Depends(get_book_service)) -> BookResponse:
    return service.get_book(book_id)


@router.post(
    "",
    response_model=BookResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_book(
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