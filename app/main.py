import logging
import time

from contextlib import asynccontextmanager
from sqlalchemy.orm import Session

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.limiter import limiter

from app.config import get_settings
from app.logging_config import configure_logging
from app.database import Base, SessionLocal, engine
from app.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.routers.book import router as book_router
from app.routers.loan import router as loan_router
from app.routers.user import router as user_router
from app.routers.reservation import router as reservation_router
from app.repositories.health import HealthRepository
from app.schemas.health import HealthResponse
from app.services.health import HealthService

settings = get_settings()

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


def get_health_service() -> HealthService:
    db: Session = SessionLocal()
    try:
        repository = HealthRepository(db)
        return HealthService(repository, settings)
    finally:
        db.close()

def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(
            "request completed",
            extra={
                "event": "http_request",
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response


    @app.exception_handler(NotFoundError)
    async def handle_not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"detail": str(exc)},
        )

    @app.exception_handler(ConflictError)
    async def handle_conflict(_: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={"detail": str(exc)},
        )

    @app.exception_handler(BusinessRuleError)
    async def handle_business_rule(_: Request, exc: BusinessRuleError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc)},
        )

    @app.get("/health", response_model=HealthResponse, tags=["health"])
    def health_check() -> HealthResponse:
        service = get_health_service()
        return service.get_health()

    app.include_router(user_router)
    app.include_router(book_router)
    app.include_router(loan_router)
    app.include_router(reservation_router)

    return app


app = create_application()