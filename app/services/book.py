from app.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models.book import Book
from app.repositories.book import BookRepository
from app.schemas.book import BookCreate, BookUpdate


class BookService:
    def __init__(self, repository: BookRepository) -> None:
        self.repository = repository

    def list_books(self) -> list[Book]:
        return self.repository.list_all()

    def get_book(self, book_id: int) -> Book:
        book = self.repository.get_by_id(book_id)
        if book is None:
            raise NotFoundError("Book not found")
        return book

    def create_book(self, payload: BookCreate) -> Book:
        if payload.isbn is not None:
            existing_book = self.repository.get_by_isbn(payload.isbn)
            if existing_book is not None:
                raise ConflictError("A book with this ISBN already exists")

        if payload.available_copies > payload.total_copies:
            raise BusinessRuleError("Available copies cannot be greater than total copies")

        return self.repository.create(
            title=payload.title,
            author=payload.author,
            isbn=payload.isbn,
            published_year=payload.published_year,
            total_copies=payload.total_copies,
            available_copies=payload.available_copies,
        )

    def update_book(self, book_id: int, payload: BookUpdate) -> Book:
        book = self.get_book(book_id)

        changes = payload.model_dump(exclude_unset=True)

        if "isbn" in changes and changes["isbn"] is not None:
            existing_book = self.repository.get_by_isbn(changes["isbn"])
            if existing_book is not None and existing_book.id != book.id:
                raise ConflictError("A book with this ISBN already exists")

        total_copies = changes.get("total_copies", book.total_copies)
        available_copies = changes.get("available_copies", book.available_copies)

        if available_copies > total_copies:
            raise BusinessRuleError("Available copies cannot be greater than total copies")

        return self.repository.update(book, **changes)

    def check_availability(self, book_id: int) -> dict[str, int | bool]:
        book = self.get_book(book_id)
        return {
            "book_id": book.id,
            "available": book.available_copies > 0,
            "available_copies": book.available_copies,
            "total_copies": book.total_copies,
        }