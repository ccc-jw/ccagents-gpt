from typing import Any

from pydantic import BaseModel, Field


class FeishuEventRequest(BaseModel):
    event_type: str
    message_type: str | None = None
    chat_id: str | None = None
    user_id: str | None = None
    text: str | None = None
    raw_event: dict[str, Any] = Field(default_factory=dict)


class FeishuInteractiveRequest(BaseModel):
    action: str
    user_id: str
    project_id: str | None = None
    escalation_id: str | None = None
    value: dict[str, Any] = Field(default_factory=dict)
