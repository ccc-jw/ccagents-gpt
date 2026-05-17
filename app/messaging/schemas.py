from pydantic import BaseModel


class AgentMessageCreateRequest(BaseModel):
    from_agent: str
    to_agent: str
    message_type: str
    phase: str
    title: str
    content: str
    related_artifacts: list[str] = []


class AgentMessageStatusRequest(BaseModel):
    status: str
