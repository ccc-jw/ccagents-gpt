from pydantic import BaseModel


class WorkerTickRequest(BaseModel):
    runner_type: str = "claude_code_cli"
    workspace_strategy: str | None = None
    phase: str | None = None
    owner_agent: str | None = None
