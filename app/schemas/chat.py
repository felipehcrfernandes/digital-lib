from typing import Any

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(description="Conversation role such as user or assistant.")
    content: str = Field(min_length=1, description="Plain text message content.")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, description="Latest user message.")
    history: list[ChatMessage] = Field(
        default_factory=list,
        description="Previous chat messages for conversational context.",
    )


class ChatActionResult(BaseModel):
    tool_name: str = Field(description="Name of the tool or action executed.")
    success: bool = Field(description="Whether the action completed successfully.")
    data: dict[str, Any] | None = Field(
        default=None,
        description="Structured action payload returned to the frontend.",
    )
    error: str | None = Field(
        default=None,
        description="Friendly error detail when the action fails.",
    )


class ChatResponse(BaseModel):
    reply: str = Field(description="Friendly assistant message shown to the user.")
    action: ChatActionResult | None = Field(
        default=None,
        description="Optional structured action result for transparency in the UI.",
    )
