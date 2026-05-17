from pydantic import BaseModel


class WorkflowTransitionRequest(BaseModel):
    from_phase: str
    to_phase: str
    reason: str
    evidence: list[str] = []
