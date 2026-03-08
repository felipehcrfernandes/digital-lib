from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class ReservationStatus(str, Enum):
    WAITING = "WAITING"
    READY_FOR_PICKUP = "READY_FOR_PICKUP"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class ReservationCreate(BaseModel):
    user_id: int
    book_id: int


class ReservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    book_id: int
    status: ReservationStatus
    created_at: datetime
    available_at: datetime | None
    expires_at: datetime | None
    fulfilled_at: datetime | None
    cancelled_at: datetime | None
    expired_at: datetime | None