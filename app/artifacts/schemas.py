from typing import Any

from pydantic import BaseModel


class ArtifactCreateRequest(BaseModel):
    task_id: str | None = None
    artifact_type: str
    name: str
    path: str
    version: str = "v1"
    created_by: str
    metadata: dict[str, Any] = {}


class ArtifactVersionCreateRequest(BaseModel):
    version: str
    path: str
    created_by: str
    change_summary: str | None = None
    metadata: dict[str, Any] = {}
