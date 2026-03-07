from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

BookTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
BookAuthor = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=255)]
BookIsbn = Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=20)]


class BookBase(BaseModel):
    title: BookTitle
    author: BookAuthor
    isbn: BookIsbn | None = None
    published_year: int | None = Field(default=None, ge=0)
    total_copies: int = Field(default=1, ge=1)
    available_copies: int = Field(default=1, ge=0)


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: BookTitle | None = None
    author: BookAuthor | None = None
    isbn: BookIsbn | None = None
    published_year: int | None = Field(default=None, ge=0)
    total_copies: int | None = Field(default=None, ge=1)
    available_copies: int | None = Field(default=None, ge=0)


class BookResponse(BookBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime