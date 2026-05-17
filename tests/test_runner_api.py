import tempfile

from fastapi.testclient import TestClient

from app.main import create_app


def make_client():
    database = tempfile.NamedTemporaryFile(delete=False)
    return TestClient(create_app(database.name))


def create_project(client):
    return client.post(
        "/api/projects",
        json={
            "name": "Runner 元数据项目",
            "description": "验证 Runner task_run 元数据闭环",
            "owner_user_id": "feishu_user_001",
            "repo_url": "https://github.com/example/app",
            "default_branch": "main",
            "initial_requirement": "需要 Runner 登记执行元数据",
        },
    ).json()["data"]["id"]


def create_task(client, project_id):
    return client.post(
        f"/api/projects/{project_id}/tasks",
        json={
            "phase": "DEVELOPMENT",
            "owner_agent": "DEV",
            "title": "实现 Runner API",
            "description": "登记 task_run 元数据",
            "input_artifacts": ["artifact_design"],
            "expected_artifacts": ["runner_metadata"],
            "max_retries": 3,
            "deadline": "2026-05-20T18:00:00+08:00",
        },
    ).json()["data"]["id"]


def create_runner_task_run(client, project_id, task_id):
    return client.post(
        "/api/runner/task-runs",
        json={
            "task_id": task_id,
            "project_id": project_id,
            "agent": "DEV",
            "runner_type": "claude_code_cli",
            "workspace_strategy": "git_worktree",
        },
    )


def test_create_and_get_runner_task_run():
    client = make_client()
    project_id = create_project(client)
    task_id = create_task(client, project_id)

    created = create_runner_task_run(client, project_id, task_id)

    assert created.status_code == 200
    body = created.json()
    assert body["success"] is True
    assert body["data"]["task_run_id"].startswith("run_")
    assert body["data"]["status"] == "created"
    assert "request_id" in body

    detail = client.get(f"/api/runner/task-runs/{body['data']['task_run_id']}")

    assert detail.status_code == 200
    data = detail.json()["data"]
    assert data["id"] == body["data"]["task_run_id"]
    assert data["task_id"] == task_id
    assert data["project_id"] == project_id
    assert data["agent_name"] == "DEV"
    assert data["runner_type"] == "claude_code_cli"
    assert data["workspace_strategy"] == "git_worktree"
    assert data["result"] is None


def test_update_runner_task_run_status():
    client = make_client()
    project_id = create_project(client)
    task_id = create_task(client, project_id)
    task_run_id = create_runner_task_run(client, project_id, task_id).json()["data"]["task_run_id"]

    response = client.post(
        f"/api/runner/task-runs/{task_run_id}/status",
        json={
            "status": "running_claude",
            "workspace_path": "/workspaces/runs/run_001",
            "logs_path": "/logs/run_001.log",
            "stdout_path": "/logs/run_001.stdout.log",
            "stderr_path": "/logs/run_001.stderr.log",
            "diff_path": "/diffs/run_001.diff",
            "summary": "Claude CLI running",
            "result": {"phase": "running"},
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "running_claude"
    assert data["workspace_path"] == "/workspaces/runs/run_001"
    assert data["logs_path"] == "/logs/run_001.log"
    assert data["stdout_path"] == "/logs/run_001.stdout.log"
    assert data["stderr_path"] == "/logs/run_001.stderr.log"
    assert data["diff_path"] == "/diffs/run_001.diff"
    assert data["summary"] == "Claude CLI running"
    assert data["result"] == {"phase": "running"}

    detail = client.get(f"/api/runner/task-runs/{task_run_id}")
    assert detail.json()["data"]["result"] == {"phase": "running"}


def test_cancel_runner_task_run_records_reason():
    client = make_client()
    project_id = create_project(client)
    task_id = create_task(client, project_id)
    task_run_id = create_runner_task_run(client, project_id, task_id).json()["data"]["task_run_id"]

    response = client.post(
        f"/api/runner/task-runs/{task_run_id}/cancel",
        json={"reason": "用户暂停项目"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "cancelled"
    assert data["summary"] == "用户暂停项目"
    assert data["result"] == {"reason": "用户暂停项目"}
