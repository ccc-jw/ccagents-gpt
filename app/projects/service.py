import json
from datetime import datetime, timezone
from uuid import uuid4

from app.core.database import get_connection
from app.projects.schemas import ProjectCreateRequest


def _now():
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row):
    return dict(row) if row else None


def _decode_event(row):
    if row is None:
        return None
    data = dict(row)
    data["payload"] = json.loads(data.pop("payload_json") or "{}")
    return data


def _record_event(database_path: str, project_id: str, event_type: str, reason: str | None = None):
    with get_connection(database_path) as connection:
        connection.execute(
            """
            INSERT INTO project_events (id, project_id, event_type, actor_type, actor_id, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"evt_{uuid4().hex}",
                project_id,
                event_type,
                "system",
                "api",
                json.dumps({"reason": reason} if reason else {}, ensure_ascii=False),
                _now(),
            ),
        )


def create_project(database_path: str, request: ProjectCreateRequest):
    project_id = f"proj_{uuid4().hex}"
    now = _now()
    with get_connection(database_path) as connection:
        connection.execute(
            """
            INSERT INTO projects (id, name, description, owner_user_id, repo_url, default_branch, status, current_phase, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 'active', 'INIT', ?, ?)
            """,
            (
                project_id,
                request.name,
                request.description,
                request.owner_user_id,
                request.repo_url,
                request.default_branch,
                now,
                now,
            ),
        )
    _record_event(database_path, project_id, "project_created", request.initial_requirement)
    return get_project(database_path, project_id)


def get_project(database_path: str, project_id: str):
    with get_connection(database_path) as connection:
        row = connection.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return _row_to_dict(row)


def list_projects(database_path: str, owner_user_id: str | None, status: str | None):
    sql = "SELECT * FROM projects WHERE 1 = 1"
    params = []
    if owner_user_id:
        sql += " AND owner_user_id = ?"
        params.append(owner_user_id)
    if status:
        sql += " AND status = ?"
        params.append(status)
    sql += " ORDER BY created_at ASC"
    with get_connection(database_path) as connection:
        rows = connection.execute(sql, params).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_project_status(database_path: str, project_id: str):
    project = get_project(database_path, project_id)
    if project is None:
        return None
    return {
        "project_id": project_id,
        "current_phase": project["current_phase"],
        "status": project["status"],
        "progress_summary": f"项目当前处于 {project['current_phase']} 阶段。",
        "risks": [],
        "pending_user_actions": [],
    }


def list_project_events(database_path: str, project_id: str, event_type: str | None):
    sql = "SELECT * FROM project_events WHERE project_id = ?"
    params = [project_id]
    if event_type:
        sql += " AND event_type = ?"
        params.append(event_type)
    sql += " ORDER BY created_at ASC"
    with get_connection(database_path) as connection:
        rows = connection.execute(sql, params).fetchall()
    return [_decode_event(row) for row in rows]


def update_project_status(database_path: str, project_id: str, status: str, event_type: str, reason: str):
    now = _now()
    with get_connection(database_path) as connection:
        connection.execute(
            "UPDATE projects SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, project_id),
        )
    _record_event(database_path, project_id, event_type, reason)
    return get_project(database_path, project_id)


def update_project_phase(
    database_path: str,
    project_id: str,
    from_phase: str,
    to_phase: str,
    event_type: str,
    reason: str,
    evidence: list[str],
):
    now = _now()
    with get_connection(database_path) as connection:
        connection.execute(
            "UPDATE projects SET current_phase = ?, updated_at = ? WHERE id = ?",
            (to_phase, now, project_id),
        )
        connection.execute(
            """
            INSERT INTO project_events (id, project_id, event_type, actor_type, actor_id, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"evt_{uuid4().hex}",
                project_id,
                event_type,
                "system",
                "workflow",
                json.dumps(
                    {"from_phase": from_phase, "to_phase": to_phase, "reason": reason, "evidence": evidence},
                    ensure_ascii=False,
                ),
                now,
            ),
        )
    return get_project(database_path, project_id)
