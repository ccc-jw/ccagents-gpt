from fastapi import APIRouter, Request

from app.automation import service
from app.core.responses import success_response
from app.tasks.schemas import TaskDispatchRequest

router = APIRouter()


def _database_path(request: Request) -> str:
    return request.app.state.database_path


@router.post("/api/projects/{project_id}/automation/tick")
def run_project_tick(project_id: str, request_body: TaskDispatchRequest, request: Request):
    return success_response(
        service.run_project_tick(
            _database_path(request),
            project_id,
            request_body.runner_type,
            request_body.workspace_strategy,
            request_body.phase,
            request_body.owner_agent,
        )
    )
