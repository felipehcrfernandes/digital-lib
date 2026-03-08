import json
import logging
import sys
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_payload: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if hasattr(record, "method"):
            log_payload["method"] = record.method

        if hasattr(record, "path"):
            log_payload["path"] = record.path

        if hasattr(record, "status_code"):
            log_payload["status_code"] = record.status_code

        if hasattr(record, "duration_ms"):
            log_payload["duration_ms"] = record.duration_ms

        if hasattr(record, "event"):
            log_payload["event"] = record.event

        if hasattr(record, "user_id"):
            log_payload["user_id"] = record.user_id

        if hasattr(record, "book_id"):
            log_payload["book_id"] = record.book_id

        if hasattr(record, "loan_id"):
            log_payload["loan_id"] = record.loan_id

        if hasattr(record, "reservation_id"):
            log_payload["reservation_id"] = record.reservation_id

        if hasattr(record, "promoted_reservation_id"):
            log_payload["promoted_reservation_id"] = record.promoted_reservation_id

        if hasattr(record, "fine_amount"):
            log_payload["fine_amount"] = str(record.fine_amount)

        if hasattr(record, "expires_at"):
            log_payload["expires_at"] = str(record.expires_at)

        return json.dumps(log_payload, ensure_ascii=True)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)