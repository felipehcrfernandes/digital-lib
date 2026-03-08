import json
import re
from typing import Any

import httpx

from app.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.llm.client import OpenAICompatibleLLMClient
from app.schemas.book import BookCreate, BookResponse
from app.schemas.chat import ChatActionResult, ChatRequest, ChatResponse
from app.schemas.loan import LoanCreate, LoanResponse
from app.schemas.reservation import ReservationCreate, ReservationResponse
from app.schemas.user import UserCreate, UserResponse
from app.services.book import BookService
from app.services.loan import LoanService
from app.services.reservation import ReservationService
from app.services.user import UserService


class ChatService:
    SYSTEM_PROMPT = """
Voce e um assistente amigavel da Biblioteca do Felipe.

Responda sempre em portugues do Brasil.
Considere que a pessoa usuaria pode ser uma bibliotecaria usando o sistema no dia a dia.
Ajude o usuario com o sistema da biblioteca usando as ferramentas disponiveis quando necessario.
Use uma ferramenta apenas quando o usuario estiver pedindo uma acao concreta ou uma consulta de dados.
Nunca invente IDs, emails, valores de inventario, estados de emprestimo ou estados de reserva.
Se o pedido estiver ambiguo, faca uma pergunta curta para esclarecer antes de agir.
Quando uma ferramenta falhar, explique o motivo em linguagem simples e amigavel.
Evite jargao tecnico, nomes internos de ferramenta e respostas com cara de JSON.
Nao use Markdown, negrito, listas com asteriscos, crases, cercas de codigo ou caracteres especiais de formatacao.
Priorize respostas curtas, claras e praticas.
Explique primeiro o que aconteceu, depois o que exige atencao ou qual e o proximo passo, se isso for relevante.
So mencione IDs quando isso realmente ajudar a localizar um registro.
Quando listar resultados, apresente a informacao de forma simples e facil de ler.
""".strip()

    def __init__(
        self,
        llm_client: OpenAICompatibleLLMClient,
        user_service: UserService,
        book_service: BookService,
        loan_service: LoanService,
        reservation_service: ReservationService,
    ) -> None:
        self.llm_client = llm_client
        self.user_service = user_service
        self.book_service = book_service
        self.loan_service = loan_service
        self.reservation_service = reservation_service

    def chat(self, payload: ChatRequest) -> ChatResponse:
        messages = self._build_messages(payload)

        try:
            llm_response = self.llm_client.create_response(
                messages=messages,
                tools=self._get_tool_definitions(),
            )
        except httpx.HTTPError:
            return ChatResponse(
                reply=(
                    "Nao consegui acessar o servico do modelo de linguagem. "
                    "Tente novamente em instantes."
                )
            )

        tool_calls = llm_response.get("tool_calls") or []
        if not tool_calls:
            return ChatResponse(
                reply=self._clean_reply_text(
                    llm_response.get("content") or "Como posso ajudar você hoje?"
                )
            )

        tool_call = tool_calls[0]
        action = self._execute_tool_call(tool_call)

        tool_payload = action.model_dump(mode="json")
        follow_up_messages = messages + [
            {
                "role": "assistant",
                "content": llm_response.get("content") or "",
                "tool_calls": tool_calls,
            },
            {
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": json.dumps(tool_payload),
            },
        ]

        try:
            final_response = self.llm_client.create_response(messages=follow_up_messages)
            reply = self._clean_reply_text(
                final_response.get("content") or self._build_fallback_reply(action)
            )
        except httpx.HTTPError:
            reply = self._clean_reply_text(self._build_fallback_reply(action))

        return ChatResponse(reply=reply, action=action)

    def _build_messages(self, payload: ChatRequest) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = [{"role": "system", "content": self.SYSTEM_PROMPT}]
        messages.extend(message.model_dump() for message in payload.history)
        messages.append({"role": "user", "content": payload.message})
        return messages

    def _execute_tool_call(self, tool_call: dict[str, Any]) -> ChatActionResult:
        function = tool_call.get("function", {})
        tool_name = function.get("name", "unknown_tool")

        try:
            arguments = json.loads(function.get("arguments") or "{}")
        except json.JSONDecodeError:
            return ChatActionResult(
                tool_name=tool_name,
                success=False,
                error="O assistente gerou argumentos inválidos para esta ação.",
            )

        try:
            result = self._run_tool(tool_name, arguments)
            return ChatActionResult(
                tool_name=tool_name,
                success=True,
                data=result,
            )
        except (BusinessRuleError, ConflictError, NotFoundError) as exc:
            return ChatActionResult(
                tool_name=tool_name,
                success=False,
                error=str(exc),
            )

    def _run_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "list_users":
            result = self.user_service.list_users(
                skip=int(arguments.get("skip", 0)),
                limit=int(arguments.get("limit", 10)),
            )
            return result.model_dump(mode="json")

        if tool_name == "create_user":
            user = self.user_service.create_user(UserCreate(**arguments))
            return UserResponse.model_validate(user).model_dump(mode="json")

        if tool_name == "list_books":
            result = self.book_service.list_books(
                skip=int(arguments.get("skip", 0)),
                limit=int(arguments.get("limit", 10)),
            )
            return result.model_dump(mode="json")

        if tool_name == "create_book":
            book = self.book_service.create_book(BookCreate(**arguments))
            return BookResponse.model_validate(book).model_dump(mode="json")

        if tool_name == "check_book_availability":
            return self.book_service.check_availability(int(arguments["book_id"]))

        if tool_name == "create_loan":
            loan = self.loan_service.create_loan(LoanCreate(**arguments))
            return LoanResponse.model_validate(loan).model_dump(mode="json")

        if tool_name == "return_loan":
            loan = self.loan_service.return_loan(int(arguments["loan_id"]))
            return LoanResponse.model_validate(loan).model_dump(mode="json")

        if tool_name == "renew_loan":
            loan = self.loan_service.renew_loan(int(arguments["loan_id"]))
            return LoanResponse.model_validate(loan).model_dump(mode="json")

        if tool_name == "create_reservation":
            reservation = self.reservation_service.create_reservation(ReservationCreate(**arguments))
            return ReservationResponse.model_validate(reservation).model_dump(mode="json")

        if tool_name == "get_reservation":
            reservation = self.reservation_service.get_reservation(int(arguments["reservation_id"]))
            return ReservationResponse.model_validate(reservation).model_dump(mode="json")

        raise BusinessRuleError("Esta ação de chat nao e permitida")

    def _build_fallback_reply(self, action: ChatActionResult) -> str:
        if action.success:
            return f"Conclui a acao {action.tool_name} com sucesso."
        return f"Nao consegui concluir a acao {action.tool_name}: {action.error}"

    def _clean_reply_text(self, text: str) -> str:
        cleaned = text.replace("**", "")
        cleaned = cleaned.replace("__", "")
        cleaned = cleaned.replace("`", "")
        cleaned = re.sub(r"^#{1,6}\s*", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"^\s*[-*]\s+", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
        return cleaned

    def _get_tool_definitions(self) -> list[dict[str, Any]]:
        return [
            self._function_tool(
                "list_users",
                "Lista usuários com paginação.",
                {
                    "type": "object",
                    "properties": {
                        "skip": {"type": "integer", "minimum": 0, "default": 0},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 10},
                    },
                },
            ),
            self._function_tool(
                "create_user",
                "Cria um novo usuário da biblioteca.",
                {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                    },
                    "required": ["name", "email"],
                },
            ),
            self._function_tool(
                "list_books",
                "Lista livros com paginaçãoo.",
                {
                    "type": "object",
                    "properties": {
                        "skip": {"type": "integer", "minimum": 0, "default": 0},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 10},
                    },
                },
            ),
            self._function_tool(
                "create_book",
                "Cria um novo livro no catálogo.",
                {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "author": {"type": "string"},
                        "isbn": {"type": "string"},
                        "published_year": {"type": "integer"},
                        "total_copies": {"type": "integer", "minimum": 1},
                        "available_copies": {"type": "integer", "minimum": 0},
                    },
                    "required": ["title", "author"],
                },
            ),
            self._function_tool(
                "check_book_availability",
                "Consulta se um livro esta disponível para empréstimo.",
                {
                    "type": "object",
                    "properties": {
                        "book_id": {"type": "integer", "minimum": 1},
                    },
                    "required": ["book_id"],
                },
            ),
            self._function_tool(
                "create_loan",
                "Cria um empréstimo para um usuario e um livro.",
                {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "integer", "minimum": 1},
                        "book_id": {"type": "integer", "minimum": 1},
                    },
                    "required": ["user_id", "book_id"],
                },
            ),
            self._function_tool(
                "return_loan",
                "Registra a devolução de um empréstimo existente.",
                {
                    "type": "object",
                    "properties": {
                        "loan_id": {"type": "integer", "minimum": 1},
                    },
                    "required": ["loan_id"],
                },
            ),
            self._function_tool(
                "renew_loan",
                "Renova uma vez um empréstimo ativo.",
                {
                    "type": "object",
                    "properties": {
                        "loan_id": {"type": "integer", "minimum": 1},
                    },
                    "required": ["loan_id"],
                },
            ),
            self._function_tool(
                "create_reservation",
                "Cria uma reserva para um livro indisponível.",
                {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "integer", "minimum": 1},
                        "book_id": {"type": "integer", "minimum": 1},
                    },
                    "required": ["user_id", "book_id"],
                },
            ),
            self._function_tool(
                "get_reservation",
                "Consulta uma reserva pelo ID.",
                {
                    "type": "object",
                    "properties": {
                        "reservation_id": {"type": "integer", "minimum": 1},
                    },
                    "required": ["reservation_id"],
                },
            ),
        ]

    def _function_tool(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            },
        }
