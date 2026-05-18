from fastapi import APIRouter

from app.core.responses import success_response
from app.feishu import service
from app.feishu.schemas import FeishuEventRequest, FeishuInteractiveRequest

router = APIRouter()


@router.post("/api/feishu/events")
def receive_event(request_body: FeishuEventRequest):
    return success_response(service.handle_event(request_body))


@router.post("/api/feishu/interactive")
def receive_interactive(request_body: FeishuInteractiveRequest):
    return success_response(service.handle_interactive(request_body))
