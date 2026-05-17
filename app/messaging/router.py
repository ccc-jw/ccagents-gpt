from fastapi import APIRouter, Request

from app.core.responses import success_response
from app.messaging import service
from app.messaging.schemas import AgentMessageCreateRequest, AgentMessageStatusRequest

router = APIRouter()


def _database_path(request: Request) -> str:
    return request.app.state.database_path


@router.post("/api/projects/{project_id}/agent-messages")
def create_message(project_id: str, request_body: AgentMessageCreateRequest, request: Request):
    return success_response(service.create_message(_database_path(request), project_id, request_body))


@router.get("/api/projects/{project_id}/agent-messages")
def list_messages(
    project_id: str,
    request: Request,
    to_agent: str | None = None,
    from_agent: str | None = None,
    message_type: str | None = None,
    status: str | None = None,
):
    return success_response(
        service.list_messages(_database_path(request), project_id, to_agent, from_agent, message_type, status)
    )


@router.get("/api/agent-messages/{message_id}")
def get_message(message_id: str, request: Request):
    return success_response(service.get_message(_database_path(request), message_id))


@router.post("/api/agent-messages/{message_id}/status")
def update_message_status(message_id: str, request_body: AgentMessageStatusRequest, request: Request):
    return success_response(service.update_message_status(_database_path(request), message_id, request_body.status))
