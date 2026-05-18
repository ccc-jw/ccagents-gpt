from fastapi import APIRouter, Request

from app.artifacts import service
from app.artifacts.schemas import ArtifactCreateRequest, ArtifactVersionCreateRequest
from app.core.responses import success_response

router = APIRouter()


def _database_path(request: Request) -> str:
    return request.app.state.database_path


@router.post("/api/projects/{project_id}/artifacts")
def create_artifact(project_id: str, request_body: ArtifactCreateRequest, request: Request):
    return success_response(service.create_artifact(_database_path(request), project_id, request_body))


@router.get("/api/projects/{project_id}/artifacts")
def list_artifacts(
    project_id: str,
    request: Request,
    artifact_type: str | None = None,
    created_by: str | None = None,
    status: str | None = None,
):
    return success_response(service.list_artifacts(_database_path(request), project_id, artifact_type, created_by, status))


@router.get("/api/artifacts/{artifact_id}")
def get_artifact(artifact_id: str, request: Request):
    return success_response(service.get_artifact(_database_path(request), artifact_id))


@router.post("/api/artifacts/{artifact_id}/versions")
def create_artifact_version(artifact_id: str, request_body: ArtifactVersionCreateRequest, request: Request):
    return success_response(service.create_artifact_version(_database_path(request), artifact_id, request_body))


@router.get("/api/artifacts/{artifact_id}/versions")
def list_artifact_versions(artifact_id: str, request: Request):
    return success_response(service.list_artifact_versions(_database_path(request), artifact_id))
