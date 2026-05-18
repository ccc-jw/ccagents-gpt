from fastapi import APIRouter, Request

from app.core.responses import success_response
from app.workers import service
from app.workers.schemas import WorkerTickRequest

router = APIRouter()


def _database_path(request: Request) -> str:
    return request.app.state.database_path


@router.post("/api/workers/tick")
def run_worker_tick(request_body: WorkerTickRequest, request: Request):
    return success_response(
        service.run_worker_tick(
            _database_path(request),
            request_body.runner_type,
            request_body.workspace_strategy,
            request_body.phase,
            request_body.owner_agent,
        )
    )
