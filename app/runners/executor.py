import subprocess

from app.runners import service


def execute_task_run(database_path: str, task_run_id: str):
    plan = service.get_task_run_execution_plan(database_path, task_run_id)
    if plan is None:
        return None
    completed = subprocess.run(plan["command"], capture_output=True, text=True, check=False)
    status = "completed" if completed.returncode == 0 else "failed"
    summary = "Runner execution completed" if status == "completed" else "Runner execution failed"
    return service.update_task_run_status(
        database_path,
        task_run_id,
        type(
            "RunnerExecutionResult",
            (),
            {
                "status": status,
                "workspace_path": plan["workspace_path"],
                "logs_path": plan["logs_path"],
                "stdout_path": plan["stdout_path"],
                "stderr_path": plan["stderr_path"],
                "diff_path": plan["diff_path"],
                "summary": summary,
                "error_type": None if status == "completed" else "process_exit",
                "error_message": None if status == "completed" else f"exit code {completed.returncode}",
                "result": {"exit_code": completed.returncode},
            },
        )(),
    )
