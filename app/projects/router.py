from fastapi import APIRouter, Request

from app.core.responses import success_response
from app.projects import service
from app.projects.schemas import ProjectActionRequest, ProjectCreateRequest

router = APIRouter()


def _database_path(request: Request) -> str:
    return request.app.state.database_path


@router.post("/api/projects")
def create_project(request_body: ProjectCreateRequest, request: Request):
    project = service.create_project(_database_path(request), request_body)
    return success_response(
        {
            "id": project["id"],
            "name": project["name"],
            "status": project["status"],
            "current_phase": project["current_phase"],
        }
    )


@router.get("/api/projects/{project_id}")
def get_project(project_id: str, request: Request):
    return success_response(service.get_project(_database_path(request), project_id))


@router.get("/api/projects/{project_id}/status")
def get_project_status(project_id: str, request: Request):
    return success_response(service.get_project_status(_database_path(request), project_id))


@router.get("/api/projects/{project_id}/events")
def list_project_events(project_id: str, request: Request, event_type: str | None = None):
    return success_response(service.list_project_events(_database_path(request), project_id, event_type))


@router.post("/api/projects/{project_id}/pause")
def pause_project(project_id: str, request_body: ProjectActionRequest, request: Request):
    return success_response(
        service.update_project_status(_database_path(request), project_id, "paused", "project_paused", request_body.reason)
    )


@router.post("/api/projects/{project_id}/resume")
def resume_project(project_id: str, request_body: ProjectActionRequest, request: Request):
    return success_response(
        service.update_project_status(_database_path(request), project_id, "active", "project_resumed", request_body.reason)
    )


@router.post("/api/projects/{project_id}/cancel")
def cancel_project(project_id: str, request_body: ProjectActionRequest, request: Request):
    return success_response(
        service.update_project_status(_database_path(request), project_id, "cancelled", "project_cancelled", request_body.reason)
    )
