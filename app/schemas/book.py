from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BookBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    author: str = Field(..., min_length=2, max_length=255)
    isbn: str | None = Field(default=None, min_length=10, max_length=20)
    published_year: int | None = Field(default=None, ge=0)
    total_copies: int = Field(default=1, ge=1)
    available_copies: int = Field(default=1, ge=0)


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    author: str | None = Field(default=None, min_length=2, max_length=255)
    isbn: str | None = Field(default=None, min_length=10, max_length=20)
    published_year: int | None = Field(default=None, ge=0)
    total_copies: int | None = Field(default=None, ge=1)
    available_copies: int | None = Field(default=None, ge=0)


class BookResponse(BookBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime