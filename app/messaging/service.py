import json
from datetime import datetime, timezone
from uuid import uuid4

from app.core.database import get_connection
from app.messaging.schemas import AgentMessageCreateRequest


def _now():
    return datetime.now(timezone.utc).isoformat()


def _decode_message(row):
    if row is None:
        return None
    data = dict(row)
    data["related_artifacts"] = json.loads(data.pop("related_artifacts_json") or "[]")
    return data


def create_message(database_path: str, project_id: str, request: AgentMessageCreateRequest):
    message_id = f"msg_{uuid4().hex}"
    now = _now()
    with get_connection(database_path) as connection:
        connection.execute(
            """
            INSERT INTO agent_messages (
                id, project_id, from_agent, to_agent, message_type, phase, title,
                content, related_artifacts_json, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            """,
            (
                message_id,
                project_id,
                request.from_agent,
                request.to_agent,
                request.message_type,
                request.phase,
                request.title,
                request.content,
                json.dumps(request.related_artifacts, ensure_ascii=False),
                now,
                now,
            ),
        )
    return get_message(database_path, message_id)


def get_message(database_path: str, message_id: str):
    with get_connection(database_path) as connection:
        row = connection.execute("SELECT * FROM agent_messages WHERE id = ?", (message_id,)).fetchone()
    return _decode_message(row)


def list_messages(
    database_path: str,
    project_id: str,
    to_agent: str | None,
    from_agent: str | None,
    message_type: str | None,
    status: str | None,
):
    sql = "SELECT * FROM agent_messages WHERE project_id = ?"
    params = [project_id]
    if to_agent:
        sql += " AND to_agent = ?"
        params.append(to_agent)
    if from_agent:
        sql += " AND from_agent = ?"
        params.append(from_agent)
    if message_type:
        sql += " AND message_type = ?"
        params.append(message_type)
    if status:
        sql += " AND status = ?"
        params.append(status)
    with get_connection(database_path) as connection:
        rows = connection.execute(sql, params).fetchall()
    return [_decode_message(row) for row in rows]


def update_message_status(database_path: str, message_id: str, status: str):
    now = _now()
    with get_connection(database_path) as connection:
        connection.execute(
            "UPDATE agent_messages SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, message_id),
        )
    return get_message(database_path, message_id)
