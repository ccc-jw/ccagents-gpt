from pydantic import BaseModel


class ProjectCreateRequest(BaseModel):
    name: str
    description: str | None = None
    owner_user_id: str
    repo_url: str | None = None
    default_branch: str = "main"
    initial_requirement: str | None = None


class ProjectActionRequest(BaseModel):
    reason: str
