import json
from datetime import datetime, timezone
from uuid import uuid4

from app.core.database import get_connection
from app.escalations import service as escalation_service
from app.escalations.schemas import EscalationCreateRequest
from app.issues.schemas import IssueCreateRequest
from app.projects import service as project_service


def _now():
    return datetime.now(timezone.utc).isoformat()


def _decode_issue(row):
    if row is None:
        return None
    data = dict(row)
    data["related_artifacts"] = json.loads(data.pop("related_artifacts_json") or "[]")
    data["reproduce_steps"] = json.loads(data.pop("reproduce_steps_json") or "[]")
    return data


def _issue_event_payload(issue):
    return {
        "issue_id": issue["id"],
        "source": issue["source"],
        "phase": issue["phase"],
        "title": issue["title"],
        "severity": issue["severity"],
        "priority": issue["priority"],
        "assigned_agent": issue["assigned_agent"],
        "status": issue["status"],
        "retry_count": issue["retry_count"],
    }


ESCALATION_OPTIONS = ["continue", "manual", "cancel", "change_requirement"]


def create_issue(database_path: str, project_id: str, request: IssueCreateRequest):
    issue_id = f"issue_{uuid4().hex}"
    now = _now()
    with get_connection(database_path) as connection:
        connection.execute(
            """
            INSERT INTO issues (
                id, project_id, source, phase, title, description, severity, priority,
                assigned_agent, related_artifacts_json, reproduce_steps_json, expected_result,
                actual_result, status, max_retries, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?, ?)
            """,
            (
                issue_id,
                project_id,
                request.source,
                request.phase,
                request.title,
                request.description,
                request.severity,
                request.priority,
                request.assigned_agent,
                json.dumps(request.related_artifacts, ensure_ascii=False),
                json.dumps(request.reproduce_steps, ensure_ascii=False),
                request.expected_result,
                request.actual_result,
                request.max_retries,
                now,
                now,
            ),
        )
    issue = get_issue(database_path, issue_id)
    project_service.record_project_event(
        database_path,
        project_id,
        "issue_created",
        _issue_event_payload(issue),
    )
    return issue


def get_issue(database_path: str, issue_id: str):
    with get_connection(database_path) as connection:
        row = connection.execute("SELECT * FROM issues WHERE id = ?", (issue_id,)).fetchone()
    return _decode_issue(row)


def list_issues(
    database_path: str,
    project_id: str,
    status: str | None,
    source: str | None,
    severity: str | None,
    assigned_agent: str | None,
):
    sql = "SELECT * FROM issues WHERE project_id = ?"
    params = [project_id]
    if status:
        sql += " AND status = ?"
        params.append(status)
    if source:
        sql += " AND source = ?"
        params.append(source)
    if severity:
        sql += " AND severity = ?"
        params.append(severity)
    if assigned_agent:
        sql += " AND assigned_agent = ?"
        params.append(assigned_agent)
    with get_connection(database_path) as connection:
        rows = connection.execute(sql, params).fetchall()
    return [_decode_issue(row) for row in rows]


def assign_issue(database_path: str, issue_id: str, assigned_agent: str):
    now = _now()
    with get_connection(database_path) as connection:
        connection.execute(
            "UPDATE issues SET assigned_agent = ?, status = 'assigned', updated_at = ? WHERE id = ?",
            (assigned_agent, now, issue_id),
        )
    issue = get_issue(database_path, issue_id)
    project_service.record_project_event(
        database_path,
        issue["project_id"],
        "issue_assigned",
        _issue_event_payload(issue),
    )
    return issue


def _get_project_owner_user_id(connection, project_id: str):
    row = connection.execute("SELECT owner_user_id FROM projects WHERE id = ?", (project_id,)).fetchone()
    return row["owner_user_id"] if row else None


def _create_issue_escalation(database_path: str, issue):
    with get_connection(database_path) as connection:
        owner_user_id = _get_project_owner_user_id(connection, issue["project_id"])
    if owner_user_id is None:
        return None
    return escalation_service.create_escalation(
        database_path,
        issue["project_id"],
        EscalationCreateRequest(
            type="issue_retry_threshold",
            phase=issue["phase"],
            source_agent=issue["assigned_agent"],
            target_user_id=owner_user_id,
            retry_count=issue["retry_count"],
            threshold=issue["max_retries"],
            summary=f"问题 {issue['id']} 已连续重开 {issue['retry_count']} 次，需要用户决策。",
            options=ESCALATION_OPTIONS,
        ),
    )


def update_issue_status(database_path: str, issue_id: str, status: str):
    now = _now()
    with get_connection(database_path) as connection:
        if status == "reopened":
            connection.execute(
                "UPDATE issues SET status = ?, retry_count = retry_count + 1, updated_at = ? WHERE id = ?",
                (status, now, issue_id),
            )
        else:
            connection.execute(
                "UPDATE issues SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, issue_id),
            )
    issue = get_issue(database_path, issue_id)
    project_service.record_project_event(
        database_path,
        issue["project_id"],
        "issue_status_updated",
        _issue_event_payload(issue),
    )
    if status == "reopened" and issue["retry_count"] == issue["max_retries"]:
        _create_issue_escalation(database_path, issue)
    return issue
