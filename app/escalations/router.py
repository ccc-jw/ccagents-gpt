from fastapi import APIRouter, Request

from app.core.responses import success_response
from app.escalations import service
from app.escalations.schemas import EscalationCreateRequest, EscalationDecisionRequest

router = APIRouter()


def _database_path(request: Request) -> str:
    return request.app.state.database_path


@router.post("/api/projects/{project_id}/escalations")
def create_escalation(project_id: str, request_body: EscalationCreateRequest, request: Request):
    return success_response(service.create_escalation(_database_path(request), project_id, request_body))


@router.get("/api/projects/{project_id}/escalations")
def list_escalations(project_id: str, request: Request):
    return success_response(service.list_escalations(_database_path(request), project_id))


@router.get("/api/escalations/{escalation_id}")
def get_escalation(escalation_id: str, request: Request):
    return success_response(service.get_escalation(_database_path(request), escalation_id))


@router.post("/api/escalations/{escalation_id}/decision")
def decide_escalation(escalation_id: str, request_body: EscalationDecisionRequest, request: Request):
    return success_response(service.decide_escalation(_database_path(request), escalation_id, request_body))
