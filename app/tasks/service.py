import json
from datetime import datetime, timezone
from uuid import uuid4

from app.core.database import get_connection
from app.tasks.schemas import TaskCreateRequest


def _now():
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row):
    return dict(row) if row else None


def _decode_task(row):
    if row is None:
        return None
    data = dict(row)
    data["input_artifacts"] = json.loads(data.pop("input_artifacts_json") or "[]")
    data["expected_artifacts"] = json.loads(data.pop("expected_artifacts_json") or "[]")
    data["blocked_by"] = json.loads(data.pop("blocked_by_json") or "[]")
    return data


def _decode_task_run(row):
    if row is None:
        return None
    data = dict(row)
    result_json = data.pop("result_json")
    data["result"] = json.loads(result_json) if result_json else None
    return data


def create_task(database_path: str, project_id: str, request: TaskCreateRequest):
    task_id = f"task_{uuid4().hex}"
    now = _now()
    with get_connection(database_path) as connection:
        connection.execute(
            """
            INSERT INTO tasks (
                id, project_id, phase, owner_agent, title, description, status, input_artifacts_json,
                expected_artifacts_json, max_retries, created_by, deadline, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                project_id,
                request.phase,
                request.owner_agent,
                request.title,
                request.description,
                json.dumps(request.input_artifacts, ensure_ascii=False),
                json.dumps(request.expected_artifacts, ensure_ascii=False),
                request.max_retries,
                request.owner_agent,
                request.deadline,
                now,
                now,
            ),
        )
    return get_task(database_path, task_id)


def get_task(database_path: str, task_id: str):
    with get_connection(database_path) as connection:
        row = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return _decode_task(row)


def list_tasks(database_path: str, project_id: str, status: str | None, phase: str | None, owner_agent: str | None):
    sql = "SELECT * FROM tasks WHERE project_id = ?"
    params = [project_id]
    if status:
        sql += " AND status = ?"
        params.append(status)
    if phase:
        sql += " AND phase = ?"
        params.append(phase)
    if owner_agent:
        sql += " AND owner_agent = ?"
        params.append(owner_agent)
    with get_connection(database_path) as connection:
        rows = connection.execute(sql, params).fetchall()
    return [_decode_task(row) for row in rows]


def list_task_runs(database_path: str, task_id: str):
    with get_connection(database_path) as connection:
        rows = connection.execute("SELECT * FROM task_runs WHERE task_id = ?", (task_id,)).fetchall()
    return [_decode_task_run(row) for row in rows]


def dispatch_pending_tasks(
    database_path: str,
    project_id: str,
    runner_type: str,
    workspace_strategy: str | None,
    phase: str | None = None,
    owner_agent: str | None = None,
):
    tasks = list_tasks(database_path, project_id, "pending", phase, owner_agent)
    dispatched = []
    for task in tasks:
        run = start_task(database_path, task["id"], runner_type, workspace_strategy)
        dispatched.append(
            {
                "task_id": task["id"],
                "task_run_id": run["task_run_id"],
                "agent_name": task["owner_agent"],
                "status": run["status"],
            }
        )
    message = "没有匹配的待调度任务。" if not dispatched else None
    return {"count": len(dispatched), "dispatched": dispatched, "message": message}


def assign_task(database_path: str, task_id: str, assigned_to: str):
    now = _now()
    with get_connection(database_path) as connection:
        connection.execute(
            "UPDATE tasks SET status = 'assigned', assigned_to = ?, updated_at = ? WHERE id = ?",
            (assigned_to, now, task_id),
        )
    return get_task(database_path, task_id)


def start_task(database_path: str, task_id: str, runner_type: str, workspace_strategy: str | None):
    task = get_task(database_path, task_id)
    run_id = f"run_{uuid4().hex}"
    now = _now()
    with get_connection(database_path) as connection:
        connection.execute(
            "UPDATE tasks SET status = 'running', updated_at = ? WHERE id = ?",
            (now, task_id),
        )
        connection.execute(
            """
            INSERT INTO task_runs (id, task_id, project_id, agent_name, runner_type, workspace_strategy, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 'created', ?, ?)
            """,
            (run_id, task_id, task["project_id"], task["owner_agent"], runner_type, workspace_strategy, now, now),
        )
    return {"task_run_id": run_id, "status": "created"}


def retry_task(database_path: str, task_id: str):
    now = _now()
    with get_connection(database_path) as connection:
        connection.execute(
            "UPDATE tasks SET status = 'pending', retry_count = retry_count + 1, updated_at = ? WHERE id = ?",
            (now, task_id),
        )
    return get_task(database_path, task_id)


def cancel_task(database_path: str, task_id: str):
    now = _now()
    with get_connection(database_path) as connection:
        connection.execute(
            "UPDATE tasks SET status = 'cancelled', updated_at = ? WHERE id = ?",
            (now, task_id),
        )
    return get_task(database_path, task_id)
