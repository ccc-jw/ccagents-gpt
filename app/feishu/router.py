from fastapi import APIRouter, Request

from app.core.responses import success_response
from app.feishu import service
from app.feishu.schemas import FeishuEventRequest, FeishuInteractiveRequest

router = APIRouter()


def _database_path(request: Request) -> str:
    return request.app.state.database_path


@router.post("/api/feishu/events")
def receive_event(request_body: FeishuEventRequest, request: Request):
    return success_response(service.handle_event(_database_path(request), request_body))


@router.post("/api/feishu/interactive")
def receive_interactive(request_body: FeishuInteractiveRequest, request: Request):
    return success_response(service.handle_interactive(_database_path(request), request_body))


@router.get("/api/feishu/projects/{project_id}/status-notification")
def get_project_status_notification(project_id: str, request: Request):
    return success_response(service.build_project_status_notification(_database_path(request), project_id))


@router.post("/api/feishu/projects/{project_id}/status-notification/send")
def send_project_status_notification(project_id: str, request: Request):
    return success_response(service.send_project_status_notification(_database_path(request), project_id))


@router.get("/api/feishu/escalations/{escalation_id}/notification")
def get_escalation_notification(escalation_id: str, request: Request):
    return success_response(service.build_escalation_notification(_database_path(request), escalation_id))


@router.post("/api/feishu/escalations/{escalation_id}/notification/send")
def send_escalation_notification(escalation_id: str, request: Request):
    return success_response(service.send_escalation_notification(_database_path(request), escalation_id))
