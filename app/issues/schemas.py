from pydantic import BaseModel


class IssueCreateRequest(BaseModel):
    source: str
    phase: str
    title: str
    description: str | None = None
    severity: str = "major"
    priority: str = "normal"
    assigned_agent: str | None = None
    related_artifacts: list[str] = []
    reproduce_steps: list[str] = []
    expected_result: str | None = None
    actual_result: str | None = None
    max_retries: int = 3


class IssueAssignRequest(BaseModel):
    assigned_agent: str


class IssueStatusRequest(BaseModel):
    status: str
    reason: str | None = None
