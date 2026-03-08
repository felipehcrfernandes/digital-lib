from fastapi.testclient import TestClient

from app.main import app
from app.routers.chat import get_chat_service
from app.schemas.chat import ChatActionResult, ChatResponse


class FakeChatService:
    def chat(self, payload):  # pragma: no cover - simple test double
        return ChatResponse(
            reply=f"Handled: {payload.message}",
            action=ChatActionResult(
                tool_name="fake_tool",
                success=True,
                data={"echo": payload.message},
            ),
        )


def test_chat_ui_page_is_served(client: TestClient) -> None:
    response = client.get("/chat/ui")

    assert response.status_code == 200
    assert "Biblioteca do Felipe" in response.text


def test_chat_endpoint_returns_structured_response(client: TestClient) -> None:
    app.dependency_overrides[get_chat_service] = lambda: FakeChatService()

    try:
        response = client.post(
            "/chat",
            json={
                "message": "create a user",
                "history": [],
            },
        )
    finally:
        app.dependency_overrides.pop(get_chat_service, None)

    assert response.status_code == 200
    assert response.json() == {
        "reply": "Handled: create a user",
        "action": {
            "tool_name": "fake_tool",
            "success": True,
            "data": {"echo": "create a user"},
            "error": None,
        },
    }
