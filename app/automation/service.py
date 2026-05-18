from app.projects import service as project_service
from app.runners import service as runner_service
from app.tasks import service as task_service


def run_project_tick(
    database_path: str,
    project_id: str,
    runner_type: str,
    workspace_strategy: str | None,
    phase: str | None = None,
    owner_agent: str | None = None,
):
    dispatch = task_service.dispatch_next_pending_task(
        database_path,
        project_id,
        runner_type,
        workspace_strategy,
        phase,
        owner_agent,
    )
    if not dispatch["dispatched"]:
        result = {"project_id": project_id, "action": "idle", "dispatch": dispatch, "execution_plan": None}
        project_service.record_project_event(database_path, project_id, "automation_tick", {"action": "idle"})
        return result
    result = {
        "project_id": project_id,
        "action": "dispatched_task",
        "dispatch": dispatch,
        "execution_plan": runner_service.get_task_run_execution_plan(database_path, dispatch["task_run_id"]),
    }
    project_service.record_project_event(
        database_path,
        project_id,
        "automation_tick",
        {"action": "dispatched_task", "task_id": dispatch["task_id"], "task_run_id": dispatch["task_run_id"]},
    )
    return result
