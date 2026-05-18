import json
import os
from datetime import datetime, timezone
from uuid import uuid4

import httpx

from app.core.database import get_connection
from app.escalations import service as escalation_service
from app.escalations.schemas import EscalationDecisionRequest
from app.feishu.schemas import FeishuEventRequest, FeishuInteractiveRequest
from app.projects import service as project_service


SUPPORTED_COMMANDS = {"status", "pause", "resume", "cancel", "help"}
ACTION_LABELS = {
    "continue": "继续自动处理",
    "manual": "转人工处理",
    "cancel": "取消项目",
    "change_requirement": "变更需求",
    "redesign": "重新设计",
}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _decode_notification(row):
    if row is None:
        return None
    data = dict(row)
    data["payload"] = json.loads(data.pop("payload_json") or "{}")
    return data


def parse_command(text: str | None):
    if not text or not text.strip().startswith("/"):
        return None, []
    parts = text.strip().split()
    command = parts[0][1:].lower()
    if command not in SUPPORTED_COMMANDS:
        return None, []
    return command, parts[1:]


def build_project_status_notification(database_path: str, project_id: str):
    project = project_service.get_project(database_path, project_id)
    if project is None:
        return None
    project_status = project_service.get_project_status(database_path, project_id)
    return {
        "project_id": project_id,
        "message_type": "interactive",
        "card": {
            "title": f"项目状态更新：{project['name']}",
            "content": project_status["progress_summary"],
            "fields": [
                {"label": "阶段", "value": project_status["current_phase"]},
                {"label": "状态", "value": project_status["status"]},
            ],
            "risks": project_status["risks"],
            "pending_user_actions": project_status["pending_user_actions"],
        },
    }


def build_escalation_notification(database_path: str, escalation_id: str):
    escalation = escalation_service.get_escalation(database_path, escalation_id)
    if escalation is None:
        return None
    return {
        "project_id": escalation["project_id"],
        "escalation_id": escalation_id,
        "message_type": "interactive",
        "card": {
            "title": f"需要用户决策：{escalation['summary']}",
            "content": (
                f"阶段：{escalation['phase']}；来源：{escalation['source_agent']}；"
                f"重试：{escalation['retry_count']}/{escalation['threshold']}"
            ),
            "actions": [
                {"label": ACTION_LABELS.get(option, option), "value": {"decision": option}}
                for option in escalation["options"]
            ],
        },
    }


def create_notification(database_path: str, project_id: str, source_type: str, source_id: str, payload: dict):
    notification_id = f"fsn_{uuid4().hex}"
    now = _now()
    with get_connection(database_path) as connection:
        connection.execute(
            """
            INSERT INTO feishu_notifications (
                id, project_id, source_type, source_id, status, payload_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, 'pending', ?, ?, ?)
            """,
            (notification_id, project_id, source_type, source_id, json.dumps(payload, ensure_ascii=False), now, now),
        )
    return get_notification(database_path, notification_id)


def create_escalation_notification(database_path: str, escalation_id: str):
    payload = build_escalation_notification(database_path, escalation_id)
    if payload is None:
        return None
    return create_notification(database_path, payload["project_id"], "escalation", escalation_id, payload)


def get_notification(database_path: str, notification_id: str):
    with get_connection(database_path) as connection:
        row = connection.execute("SELECT * FROM feishu_notifications WHERE id = ?", (notification_id,)).fetchone()
    return _decode_notification(row)


def list_notifications(database_path: str, project_id: str):
    with get_connection(database_path) as connection:
        rows = connection.execute(
            "SELECT * FROM feishu_notifications WHERE project_id = ? ORDER BY created_at ASC",
            (project_id,),
        ).fetchall()
    return [_decode_notification(row) for row in rows]


def _update_notification_delivery(
    database_path: str,
    notification_id: str,
    status: str,
    reason: str | None,
    webhook_status_code: int | None,
):
    with get_connection(database_path) as connection:
        connection.execute(
            """
            UPDATE feishu_notifications
            SET status = ?, reason = ?, webhook_status_code = ?, updated_at = ?
            WHERE id = ?
            """,
            (status, reason, webhook_status_code, _now(), notification_id),
        )
    return get_notification(database_path, notification_id)


def send_notification(database_path: str, notification_id: str):
    notification = get_notification(database_path, notification_id)
    if notification is None:
        return None
    webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
    if not webhook_url:
        _update_notification_delivery(
            database_path,
            notification_id,
            "skipped",
            "feishu_webhook_url_not_configured",
            None,
        )
        return {"sent": False, "reason": "feishu_webhook_url_not_configured", "payload": notification["payload"]}
    response = httpx.post(webhook_url, json=notification["payload"], timeout=10)
    _update_notification_delivery(database_path, notification_id, "sent", None, response.status_code)
    return {"sent": True, "status_code": response.status_code, "payload": notification["payload"]}


def send_project_status_notification(database_path: str, project_id: str):
    payload = build_project_status_notification(database_path, project_id)
    webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
    if not webhook_url:
        return {"sent": False, "reason": "feishu_webhook_url_not_configured", "payload": payload}
    response = httpx.post(webhook_url, json=payload, timeout=10)
    return {"sent": True, "status_code": response.status_code, "payload": payload}


def send_escalation_notification(database_path: str, escalation_id: str):
    payload = build_escalation_notification(database_path, escalation_id)
    webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
    if not webhook_url:
        return {"sent": False, "reason": "feishu_webhook_url_not_configured", "payload": payload}
    response = httpx.post(webhook_url, json=payload, timeout=10)
    return {"sent": True, "status_code": response.status_code, "payload": payload}


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
                if decision == "change_requirement":
                    project = project_service.get_project(database_path, request.project_id)
                    project_service.update_project_phase(
                        database_path,
                        request.project_id,
                        project["current_phase"],
                        "REQUIREMENT_REVISION",
                        "project_requirement_change_requested",
                        "飞书升级决策变更需求",
                        [],
                    )
                    response["project_status"] = project_service.get_project_status(database_path, request.project_id)
                    response["reply_text"] = "项目已根据升级决策进入需求修订。"
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
