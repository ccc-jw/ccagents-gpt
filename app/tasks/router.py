from fastapi import APIRouter, Request

from app.core.responses import success_response
from app.tasks import service
from app.tasks.schemas import TaskAssignRequest, TaskCreateRequest, TaskReasonRequest, TaskStartRequest

router = APIRouter()


def _database_path(request: Request) -> str:
    return request.app.state.database_path


@router.post("/api/projects/{project_id}/tasks")
def create_task(project_id: str, request_body: TaskCreateRequest, request: Request):
    task = service.create_task(_database_path(request), project_id, request_body)
    return success_response({"id": task["id"], "status": task["status"]})


@router.get("/api/projects/{project_id}/tasks")
def list_tasks(
    project_id: str,
    request: Request,
    status: str | None = None,
    phase: str | None = None,
    owner_agent: str | None = None,
):
    return success_response(service.list_tasks(_database_path(request), project_id, status, phase, owner_agent))


@router.post("/api/tasks/{task_id}/assign")
def assign_task(task_id: str, request_body: TaskAssignRequest, request: Request):
    return success_response(service.assign_task(_database_path(request), task_id, request_body.assigned_to))


@router.post("/api/tasks/{task_id}/start")
def start_task(task_id: str, request_body: TaskStartRequest, request: Request):
    return success_response(
        service.start_task(_database_path(request), task_id, request_body.runner_type, request_body.workspace_strategy)
    )


@router.post("/api/tasks/{task_id}/retry")
def retry_task(task_id: str, request_body: TaskReasonRequest, request: Request):
    return success_response(service.retry_task(_database_path(request), task_id))


@router.post("/api/tasks/{task_id}/cancel")
def cancel_task(task_id: str, request_body: TaskReasonRequest, request: Request):
    return success_response(service.cancel_task(_database_path(request), task_id))
