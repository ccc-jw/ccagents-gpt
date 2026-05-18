from app.escalations import service as escalation_service
from app.escalations.schemas import EscalationDecisionRequest
from app.feishu.schemas import FeishuEventRequest, FeishuInteractiveRequest
from app.projects import service as project_service


SUPPORTED_COMMANDS = {"status", "pause", "resume", "cancel", "help"}


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
    if command == "pause" and args:
        project = project_service.get_project(database_path, args[0])
        response["handled"] = project is not None
        if project:
            project_service.update_project_status(database_path, args[0], "paused", "project_paused", "飞书命令暂停项目")
            response["project_status"] = project_service.get_project_status(database_path, args[0])
            response["reply_text"] = "项目已暂停。"
        else:
            response["reply_text"] = "项目不存在"
    if command == "resume" and args:
        project = project_service.get_project(database_path, args[0])
        response["handled"] = project is not None
        if project:
            project_service.update_project_status(database_path, args[0], "active", "project_resumed", "飞书命令恢复项目")
            response["project_status"] = project_service.get_project_status(database_path, args[0])
            response["reply_text"] = "项目已恢复。"
        else:
            response["reply_text"] = "项目不存在"
    if command == "cancel" and args:
        project = project_service.get_project(database_path, args[0])
        response["handled"] = project is not None
        if project:
            project_service.update_project_status(database_path, args[0], "cancelled", "project_cancelled", "飞书命令取消项目")
            response["project_status"] = project_service.get_project_status(database_path, args[0])
            response["reply_text"] = "项目已取消。"
        else:
            response["reply_text"] = "项目不存在"
    return response


def handle_interactive(database_path: str, request: FeishuInteractiveRequest):
    response = {
        "accepted": True,
        "source": "feishu",
        "action": request.action,
        "user_id": request.user_id,
        "project_id": request.project_id,
        "escalation_id": request.escalation_id,
        "value": request.value,
        "handled": False,
    }
    if request.action == "escalation_decision" and request.escalation_id:
        decision = request.value.get("decision")
        comment = request.value.get("comment")
        if decision:
            response["escalation"] = escalation_service.decide_escalation(
                database_path,
                request.escalation_id,
                EscalationDecisionRequest(decision=decision, comment=comment),
            )
            response["handled"] = True
            if request.project_id and project_service.get_project(database_path, request.project_id):
                if decision == "continue":
                    project_service.update_project_status(
                        database_path,
                        request.project_id,
                        "active",
                        "project_resumed",
                        "飞书升级决策继续项目",
                    )
                    response["project_status"] = project_service.get_project_status(database_path, request.project_id)
                    response["reply_text"] = "项目已根据升级决策继续。"
                if decision == "manual":
                    project_service.update_project_status(
                        database_path,
                        request.project_id,
                        "paused",
                        "project_paused",
                        "飞书升级决策转人工处理",
                    )
                    response["project_status"] = project_service.get_project_status(database_path, request.project_id)
                    response["reply_text"] = "项目已根据升级决策暂停，等待人工处理。"
                if decision == "cancel":
                    project_service.update_project_status(
                        database_path,
                        request.project_id,
                        "cancelled",
                        "project_cancelled",
                        "飞书升级决策取消项目",
                    )
                    response["project_status"] = project_service.get_project_status(database_path, request.project_id)
                    response["reply_text"] = "项目已根据升级决策取消。"
    return response
