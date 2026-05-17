from fastapi import APIRouter, Request

from app.core.responses import success_response
from app.issues import service
from app.issues.schemas import IssueAssignRequest, IssueCreateRequest, IssueStatusRequest

router = APIRouter()


def _database_path(request: Request) -> str:
    return request.app.state.database_path


@router.post("/api/projects/{project_id}/issues")
def create_issue(project_id: str, request_body: IssueCreateRequest, request: Request):
    return success_response(service.create_issue(_database_path(request), project_id, request_body))


@router.get("/api/projects/{project_id}/issues")
def list_issues(
    project_id: str,
    request: Request,
    status: str | None = None,
    source: str | None = None,
    severity: str | None = None,
    assigned_agent: str | None = None,
):
    return success_response(
        service.list_issues(_database_path(request), project_id, status, source, severity, assigned_agent)
    )


@router.get("/api/issues/{issue_id}")
def get_issue(issue_id: str, request: Request):
    return success_response(service.get_issue(_database_path(request), issue_id))


@router.post("/api/issues/{issue_id}/assign")
def assign_issue(issue_id: str, request_body: IssueAssignRequest, request: Request):
    return success_response(service.assign_issue(_database_path(request), issue_id, request_body.assigned_agent))


@router.post("/api/issues/{issue_id}/status")
def update_issue_status(issue_id: str, request_body: IssueStatusRequest, request: Request):
    return success_response(service.update_issue_status(_database_path(request), issue_id, request_body.status))
