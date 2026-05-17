from pydantic import BaseModel


class ReviewCreateRequest(BaseModel):
    type: str
    phase: str
    owner_agent: str
    participants: list[str]
    input_artifacts: list[str] = []


class ReviewCommentRequest(BaseModel):
    reviewer_agent: str
    status: str
    severity: str = "minor"
    comment: str
    required_change: str | None = None
    related_artifact: str | None = None


class ReviewCompleteRequest(BaseModel):
    conclusion: str
    summary: str
