from fastapi import APIRouter, Request

from app.core.responses import success_response
from app.runners import service
from app.runners.schemas import TaskRunCancelRequest, TaskRunCreateRequest, TaskRunStatusUpdateRequest

router = APIRouter()


def _database_path(request: Request) -> str:
    return request.app.state.database_path


@router.post("/api/runner/task-runs")
def create_task_run(request_body: TaskRunCreateRequest, request: Request):
    return success_response(service.create_task_run(_database_path(request), request_body))


@router.get("/api/runner/task-runs/{task_run_id}")
def get_task_run(task_run_id: str, request: Request):
    return success_response(service.get_task_run(_database_path(request), task_run_id))


@router.post("/api/runner/task-runs/{task_run_id}/status")
def update_task_run_status(task_run_id: str, request_body: TaskRunStatusUpdateRequest, request: Request):
    return success_response(service.update_task_run_status(_database_path(request), task_run_id, request_body))


@router.post("/api/runner/task-runs/{task_run_id}/cancel")
def cancel_task_run(task_run_id: str, request_body: TaskRunCancelRequest, request: Request):
    return success_response(service.cancel_task_run(_database_path(request), task_run_id, request_body.reason))
