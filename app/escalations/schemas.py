from pydantic import BaseModel


class EscalationCreateRequest(BaseModel):
    type: str
    phase: str
    source_agent: str | None = None
    target_user_id: str
    retry_count: int
    threshold: int = 3
    summary: str
    options: list[str]


class EscalationDecisionRequest(BaseModel):
    decision: str
    comment: str | None = None
