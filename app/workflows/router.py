from fastapi import APIRouter, HTTPException, Request

from app.core.responses import success_response
from app.workflows import service
from app.workflows.schemas import WorkflowTransitionRequest

router = APIRouter()


def _database_path(request: Request) -> str:
    return request.app.state.database_path


@router.get("/api/projects/{project_id}/workflow")
def get_workflow(project_id: str, request: Request):
    return success_response(service.get_workflow(_database_path(request), project_id))


@router.post("/api/projects/{project_id}/workflow/advance")
def advance_workflow(project_id: str, request_body: WorkflowTransitionRequest, request: Request):
    try:
        return success_response(service.advance_workflow(_database_path(request), project_id, request_body))
    except service.WorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/projects/{project_id}/workflow/reject")
def reject_workflow(project_id: str, request_body: WorkflowTransitionRequest, request: Request):
    try:
        return success_response(service.reject_workflow(_database_path(request), project_id, request_body))
    except service.WorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
