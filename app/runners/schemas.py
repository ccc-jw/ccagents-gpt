from typing import Any

from pydantic import BaseModel


class TaskRunCreateRequest(BaseModel):
    task_id: str
    project_id: str
    agent: str
    runner_type: str = "claude_code_cli"
    workspace_strategy: str | None = None


class TaskRunCancelRequest(BaseModel):
    reason: str


class TaskRunStatusUpdateRequest(BaseModel):
    status: str
    workspace_path: str | None = None
    logs_path: str | None = None
    stdout_path: str | None = None
    stderr_path: str | None = None
    diff_path: str | None = None
    summary: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    result: dict[str, Any] | None = None
