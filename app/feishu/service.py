from app.feishu.schemas import FeishuEventRequest, FeishuInteractiveRequest


SUPPORTED_COMMANDS = {"status", "pause", "resume", "help"}


def parse_command(text: str | None):
    if not text or not text.strip().startswith("/"):
        return None, []
    parts = text.strip().split()
    command = parts[0][1:].lower()
    if command not in SUPPORTED_COMMANDS:
        return None, []
    return command, parts[1:]


def handle_event(request: FeishuEventRequest):
    command, args = parse_command(request.text)
    return {
        "accepted": True,
        "source": "feishu",
        "event_type": request.event_type,
        "message_type": request.message_type,
        "chat_id": request.chat_id,
        "user_id": request.user_id,
        "text": request.text,
        "command": command,
        "args": args,
    }


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
