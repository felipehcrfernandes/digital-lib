from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.book import Book


class BookRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(self, *, skip: int = 0, limit: int = 10) -> list[Book]:
        statement = select(Book).order_by(Book.id).offset(skip).limit(limit)
        return list(self.db.scalars(statement).all())

    def count_all(self) -> int:
        statement = select(func.count()).select_from(Book)
        return self.db.scalar(statement) or 0

    def get_by_id(self, book_id: int) -> Book | None:
        return self.db.get(Book, book_id)

    def get_by_isbn(self, isbn: str) -> Book | None:
        statement = select(Book).where(Book.isbn == isbn)
        return self.db.scalar(statement)

    def create(
        self,
        *,
        title: str,
        author: str,
        isbn: str | None,
        published_year: int | None,
        total_copies: int,
        available_copies: int,
    ) -> Book:
        book = Book(
            title=title,
            author=author,
            isbn=isbn,
            published_year=published_year,
            total_copies=total_copies,
            available_copies=available_copies,
        )
        self.db.add(book)
        self.db.commit()
        self.db.refresh(book)
        return book

    def update(self, book: Book, **changes: object) -> Book:
        for field, value in changes.items():
            setattr(book, field, value)

        self.db.add(book)
        self.db.commit()
        self.db.refresh(book)
        return book