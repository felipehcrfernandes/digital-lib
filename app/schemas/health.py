from datetime import datetime

from pydantic import BaseModel


class DatabaseHealthResponse(BaseModel):
    status: str


class HealthMetricsResponse(BaseModel):
    users: int
    books: int
    loans_total: int
    loans_active: int
    loans_overdue: int
    reservations_total: int
    reservations_waiting: int
    reservations_ready_for_pickup: int


class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    timestamp: datetime
    database: DatabaseHealthResponse
    metrics: HealthMetricsResponse