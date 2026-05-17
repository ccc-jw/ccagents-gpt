import json
from datetime import datetime, timezone
from uuid import uuid4

from app.core.database import get_connection
from app.runners.schemas import TaskRunCreateRequest, TaskRunStatusUpdateRequest


def _now():
    return datetime.now(timezone.utc).isoformat()


def _decode_task_run(row):
    if row is None:
        return None
    data = dict(row)
    result_json = data.pop("result_json")
    data["result"] = json.loads(result_json) if result_json else None
    return data


def create_task_run(database_path: str, request: TaskRunCreateRequest):
    task_run_id = f"run_{uuid4().hex}"
    now = _now()
    with get_connection(database_path) as connection:
        connection.execute(
            """
            INSERT INTO task_runs (
                id, task_id, project_id, agent_name, runner_type, workspace_strategy,
                status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 'created', ?, ?)
            """,
            (
                task_run_id,
                request.task_id,
                request.project_id,
                request.agent,
                request.runner_type,
                request.workspace_strategy,
                now,
                now,
            ),
        )
    return {"task_run_id": task_run_id, "status": "created"}


def get_task_run(database_path: str, task_run_id: str):
    with get_connection(database_path) as connection:
        row = connection.execute("SELECT * FROM task_runs WHERE id = ?", (task_run_id,)).fetchone()
    return _decode_task_run(row)


def update_task_run_status(database_path: str, task_run_id: str, request: TaskRunStatusUpdateRequest):
    now = _now()
    with get_connection(database_path) as connection:
        connection.execute(
            """
            UPDATE task_runs
            SET status = ?, workspace_path = ?, logs_path = ?, stdout_path = ?, stderr_path = ?,
                diff_path = ?, summary = ?, error_type = ?, error_message = ?, result_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                request.status,
                request.workspace_path,
                request.logs_path,
                request.stdout_path,
                request.stderr_path,
                request.diff_path,
                request.summary,
                request.error_type,
                request.error_message,
                json.dumps(request.result, ensure_ascii=False) if request.result is not None else None,
                now,
                task_run_id,
            ),
        )
    return get_task_run(database_path, task_run_id)


def cancel_task_run(database_path: str, task_run_id: str, reason: str):
    now = _now()
    with get_connection(database_path) as connection:
        connection.execute(
            """
            UPDATE task_runs
            SET status = 'cancelled', summary = ?, result_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (reason, json.dumps({"reason": reason}, ensure_ascii=False), now, task_run_id),
        )
    return get_task_run(database_path, task_run_id)
