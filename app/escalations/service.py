import json
from datetime import datetime, timezone
from uuid import uuid4

from app.core.database import get_connection
from app.escalations.schemas import EscalationCreateRequest, EscalationDecisionRequest
from app.feishu import service as feishu_service
from app.projects import service as project_service


def _now():
    return datetime.now(timezone.utc).isoformat()


def _decode_escalation(row):
    if row is None:
        return None
    data = dict(row)
    data["options"] = json.loads(data.pop("options_json"))
    return data


def _escalation_event_payload(escalation):
    return {
        "escalation_id": escalation["id"],
        "type": escalation["type"],
        "phase": escalation["phase"],
        "source_agent": escalation["source_agent"],
        "target_user_id": escalation["target_user_id"],
        "status": escalation["status"],
        "retry_count": escalation["retry_count"],
        "threshold": escalation["threshold"],
        "decision": escalation["decision"],
        "decision_comment": escalation["decision_comment"],
    }


def create_escalation(database_path: str, project_id: str, request: EscalationCreateRequest):
    escalation_id = f"esc_{uuid4().hex}"
    now = _now()
    with get_connection(database_path) as connection:
        connection.execute(
            """
            INSERT INTO escalations (
                id, project_id, type, phase, source_agent, target_user_id, status,
                retry_count, threshold, summary, options_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 'pending_user_decision', ?, ?, ?, ?, ?, ?)
            """,
            (
                escalation_id,
                project_id,
                request.type,
                request.phase,
                request.source_agent,
                request.target_user_id,
                request.retry_count,
                request.threshold,
                request.summary,
                json.dumps(request.options, ensure_ascii=False),
                now,
                now,
            ),
        )
    escalation = get_escalation(database_path, escalation_id)
    project_service.record_project_event(
        database_path,
        project_id,
        "escalation_created",
        _escalation_event_payload(escalation),
    )
    feishu_service.create_escalation_notification(database_path, escalation_id)
    return escalation


def get_escalation(database_path: str, escalation_id: str):
    with get_connection(database_path) as connection:
        row = connection.execute("SELECT * FROM escalations WHERE id = ?", (escalation_id,)).fetchone()
    return _decode_escalation(row)


def list_escalations(database_path: str, project_id: str):
    with get_connection(database_path) as connection:
        rows = connection.execute("SELECT * FROM escalations WHERE project_id = ?", (project_id,)).fetchall()
    return [_decode_escalation(row) for row in rows]


def decide_escalation(database_path: str, escalation_id: str, request: EscalationDecisionRequest):
    now = _now()
    with get_connection(database_path) as connection:
        connection.execute(
            """
            UPDATE escalations
            SET status = 'decided', decision = ?, decision_comment = ?, decided_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (request.decision, request.comment, now, now, escalation_id),
        )
    escalation = get_escalation(database_path, escalation_id)
    if escalation is None:
        return None
    project_service.record_project_event(
        database_path,
        escalation["project_id"],
        "escalation_decided",
        _escalation_event_payload(escalation),
    )
    return escalation
