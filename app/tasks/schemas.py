from pydantic import BaseModel


class TaskCreateRequest(BaseModel):
    phase: str
    owner_agent: str
    title: str
    description: str | None = None
    input_artifacts: list[str] = []
    expected_artifacts: list[str] = []
    max_retries: int = 3
    deadline: str | None = None


class TaskAssignRequest(BaseModel):
    assigned_to: str


class TaskStartRequest(BaseModel):
    runner_type: str = "claude_code_cli"
    workspace_strategy: str | None = None


class TaskDispatchRequest(BaseModel):
    runner_type: str = "claude_code_cli"
    workspace_strategy: str | None = None


class TaskReasonRequest(BaseModel):
    reason: str
