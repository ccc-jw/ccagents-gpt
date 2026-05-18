from typing import Any

from pydantic import BaseModel, Field


class AgentCreateRequest(BaseModel):
    name: str
    role: str
    description: str | None = None
    enabled: bool = True
    model_overrides: dict[str, Any] = Field(default_factory=dict, alias="model_config")


class AgentEnabledRequest(BaseModel):
    enabled: bool
