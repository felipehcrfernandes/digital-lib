from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class LoanStatus(str, Enum):
    ACTIVE = "ACTIVE"
    RETURNED = "RETURNED"
    OVERDUE = "OVERDUE"


class LoanCreate(BaseModel):
    user_id: int
    book_id: int


class LoanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    book_id: int
    loan_date: datetime
    due_date: datetime
    return_date: datetime | None
    fine_amount: Decimal = Field(
        max_digits=10,
        decimal_places=2,
        examples=["0.00"],
        description="Late fee amount in BRL.",
    )
    status: LoanStatus
    created_at: datetime