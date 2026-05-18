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
def receive_interactive(request_body: FeishuInteractiveRequest):
    return success_response(service.handle_interactive(request_body))
