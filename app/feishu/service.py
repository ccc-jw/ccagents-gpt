from app.feishu.schemas import FeishuEventRequest, FeishuInteractiveRequest
from app.projects import service as project_service


SUPPORTED_COMMANDS = {"status", "pause", "resume", "help"}


def parse_command(text: str | None):
    if not text or not text.strip().startswith("/"):
        return None, []
    parts = text.strip().split()
    command = parts[0][1:].lower()
    if command not in SUPPORTED_COMMANDS:
        return None, []
    return command, parts[1:]


def handle_event(database_path: str, request: FeishuEventRequest):
    command, args = parse_command(request.text)
    response = {
        "accepted": True,
        "source": "feishu",
        "event_type": request.event_type,
        "message_type": request.message_type,
        "chat_id": request.chat_id,
        "user_id": request.user_id,
        "text": request.text,
        "command": command,
        "args": args,
        "handled": False,
    }
    if command == "status" and args:
        project_status = project_service.get_project_status(database_path, args[0])
        response["handled"] = True
        response["project_status"] = project_status
        response["reply_text"] = project_status["progress_summary"] if project_status else "项目不存在"
    return response


def handle_interactive(request: FeishuInteractiveRequest):
    return {
        "accepted": True,
        "source": "feishu",
        "action": request.action,
        "user_id": request.user_id,
        "project_id": request.project_id,
        "escalation_id": request.escalation_id,
        "value": request.value,
    }
