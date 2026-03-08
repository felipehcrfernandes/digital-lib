from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.limiter import limiter
from app.llm.client import OpenAICompatibleLLMClient
from app.repositories.book import BookRepository
from app.repositories.loan import LoanRepository
from app.repositories.reservation import ReservationRepository
from app.repositories.user import UserRepository
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.book import BookService
from app.services.chat import ChatService
from app.services.loan import LoanService
from app.services.reservation import ReservationService
from app.services.user import UserService

router = APIRouter(prefix="/chat", tags=["chat"])

CHAT_UI_FILE = Path(__file__).resolve().parents[1] / "static" / "chat.html"


def get_chat_service(db: Session = Depends(get_db)) -> ChatService:
    settings = get_settings()

    user_repository = UserRepository(db)
    book_repository = BookRepository(db)
    loan_repository = LoanRepository(db)
    reservation_repository = ReservationRepository(db)

    user_service = UserService(user_repository)
    book_service = BookService(book_repository)
    reservation_service = ReservationService(
        reservation_repository=reservation_repository,
        user_repository=user_repository,
        book_repository=book_repository,
    )
    loan_service = LoanService(
        loan_repository=loan_repository,
        user_repository=user_repository,
        book_repository=book_repository,
        reservation_service=reservation_service,
    )

    llm_client = OpenAICompatibleLLMClient(settings)
    return ChatService(
        llm_client=llm_client,
        user_service=user_service,
        book_service=book_service,
        loan_service=loan_service,
        reservation_service=reservation_service,
    )


@router.get("/ui", include_in_schema=False)
def get_chat_ui() -> FileResponse:
    return FileResponse(CHAT_UI_FILE)


@router.post("", response_model=ChatResponse)
@limiter.limit("10/minute")
def chat(
    request: Request,
    payload: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    return service.chat(payload)
