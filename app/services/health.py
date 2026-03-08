from datetime import datetime, timezone

from app.config import Settings
from app.repositories.health import HealthRepository
from app.schemas.health import (
    DatabaseHealthResponse,
    HealthMetricsResponse,
    HealthResponse,
)


class HealthService:
    def __init__(self, repository: HealthRepository, settings: Settings) -> None:
        self.repository = repository
        self.settings = settings

    def get_health(self) -> HealthResponse:
        database_ok = self.repository.check_database()

        status = "ok" if database_ok else "degraded"

        return HealthResponse(
            status=status,
            app_name=self.settings.app_name,
            version=self.settings.app_version,
            timestamp=datetime.now(timezone.utc),
            database=DatabaseHealthResponse(
                status="ok" if database_ok else "error",
            ),
            metrics=HealthMetricsResponse(
                users=self.repository.count_users(),
                books=self.repository.count_books(),
                loans_total=self.repository.count_loans_total(),
                loans_active=self.repository.count_loans_active(),
                loans_overdue=self.repository.count_loans_overdue(),
                reservations_total=self.repository.count_reservations_total(),
                reservations_waiting=self.repository.count_reservations_waiting(),
                reservations_ready_for_pickup=self.repository.count_reservations_ready_for_pickup(),
            ),
        )