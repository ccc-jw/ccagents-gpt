from app.automation import service as automation_service
from app.projects import service as project_service


def run_worker_tick(
    database_path: str,
    runner_type: str,
    workspace_strategy: str | None,
    phase: str | None = None,
    owner_agent: str | None = None,
):
    projects = project_service.list_projects(database_path, None, "active")
    for project in projects:
        tick = automation_service.run_project_tick(
            database_path,
            project["id"],
            runner_type,
            workspace_strategy,
            phase,
            owner_agent,
        )
        if tick["action"] == "dispatched_task":
            dispatch = tick["dispatch"]
            project_service.record_project_event(
                database_path,
                project["id"],
                "worker_tick",
                {
                    "action": "project_ticked",
                    "task_id": dispatch["task_id"],
                    "task_run_id": dispatch["task_run_id"],
                },
            )
            return {"action": "project_ticked", "project_id": project["id"], "tick": tick}
    return {"action": "idle", "message": "没有可自动推进的项目。"}
