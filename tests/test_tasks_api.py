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
            "name": "用户登录功能",
            "description": "实现账号密码登录、错误提示和权限校验",
            "owner_user_id": "feishu_user_001",
            "repo_url": "https://github.com/example/app",
            "default_branch": "main",
            "initial_requirement": "需要实现登录功能",
        },
    ).json()["data"]["id"]


def create_task(client, project_id, title="实现登录接口", owner_agent="DEV"):
    return client.post(
        f"/api/projects/{project_id}/tasks",
        json={
            "phase": "DEVELOPMENT",
            "owner_agent": owner_agent,
            "title": title,
            "description": "根据 PRD 和详细设计实现登录接口",
            "input_artifacts": ["artifact_prd_final", "artifact_detail_design"],
            "expected_artifacts": ["self_test_report", "source_code_diff"],
            "max_retries": 3,
            "deadline": "2026-05-20T18:00:00+08:00",
        },
    )


def test_create_task_for_project():
    client = make_client()
    project_id = create_project(client)

    response = create_task(client, project_id)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["id"].startswith("task_")
    assert body["data"]["status"] == "pending"
    assert "request_id" in body


def test_list_tasks_filters_by_status_phase_and_owner_agent():
    client = make_client()
    project_id = create_project(client)
    create_task(client, project_id, title="实现登录接口", owner_agent="DEV")
    create_task(client, project_id, title="编写测试用例", owner_agent="TEST")

    response = client.get(
        f"/api/projects/{project_id}/tasks",
        params={"status": "pending", "phase": "DEVELOPMENT", "owner_agent": "DEV"},
    )

    assert response.status_code == 200
    tasks = response.json()["data"]
    assert len(tasks) == 1
    assert tasks[0]["title"] == "实现登录接口"
    assert tasks[0]["owner_agent"] == "DEV"


def test_get_task_returns_decoded_task_detail():
    client = make_client()
    project_id = create_project(client)
    task_id = create_task(client, project_id).json()["data"]["id"]

    response = client.get(f"/api/tasks/{task_id}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == task_id
    assert data["project_id"] == project_id
    assert data["input_artifacts"] == ["artifact_prd_final", "artifact_detail_design"]
    assert data["expected_artifacts"] == ["self_test_report", "source_code_diff"]
    assert data["blocked_by"] == []
    assert "input_artifacts_json" not in data
    assert "expected_artifacts_json" not in data


def test_list_task_runs_returns_runs_for_task():
    client = make_client()
    project_id = create_project(client)
    task_id = create_task(client, project_id).json()["data"]["id"]
    started = client.post(
        f"/api/tasks/{task_id}/start",
        json={"runner_type": "claude_code_cli", "workspace_strategy": "git_worktree"},
    )

    response = client.get(f"/api/tasks/{task_id}/runs")

    assert response.status_code == 200
    runs = response.json()["data"]
    assert len(runs) == 1
    assert runs[0]["id"] == started.json()["data"]["task_run_id"]
    assert runs[0]["task_id"] == task_id
    assert runs[0]["project_id"] == project_id
    assert runs[0]["agent_name"] == "DEV"
    assert runs[0]["runner_type"] == "claude_code_cli"
    assert runs[0]["workspace_strategy"] == "git_worktree"
    assert runs[0]["status"] == "created"
    assert runs[0]["result"] is None


def test_list_task_runs_reflects_runner_status_update():
    client = make_client()
    project_id = create_project(client)
    task_id = create_task(client, project_id).json()["data"]["id"]
    created = client.post(
        "/api/runner/task-runs",
        json={
            "task_id": task_id,
            "project_id": project_id,
            "agent": "DEV",
            "runner_type": "claude_code_cli",
            "workspace_strategy": "git_worktree",
        },
    )
    task_run_id = created.json()["data"]["task_run_id"]
    client.post(
        f"/api/runner/task-runs/{task_run_id}/status",
        json={"status": "completed", "summary": "自测通过", "result": {"tests": "passed"}},
    )

    response = client.get(f"/api/tasks/{task_id}/runs")

    assert response.status_code == 200
    runs = response.json()["data"]
    assert len(runs) == 1
    assert runs[0]["id"] == task_run_id
    assert runs[0]["status"] == "completed"
    assert runs[0]["summary"] == "自测通过"
    assert runs[0]["result"] == {"tests": "passed"}


def test_assign_start_retry_and_cancel_task():
    client = make_client()
    project_id = create_project(client)
    task_id = create_task(client, project_id).json()["data"]["id"]

    assigned = client.post(f"/api/tasks/{task_id}/assign", json={"assigned_to": "DEV"})
    assert assigned.status_code == 200
    assert assigned.json()["data"]["status"] == "assigned"
    assert assigned.json()["data"]["assigned_to"] == "DEV"

    started = client.post(
        f"/api/tasks/{task_id}/start",
        json={"runner_type": "claude_code_cli", "workspace_strategy": "git_worktree"},
    )
    assert started.status_code == 200
    assert started.json()["data"]["task_run_id"].startswith("run_")
    assert started.json()["data"]["status"] == "created"

    retried = client.post(f"/api/tasks/{task_id}/retry", json={"reason": "修复测试失败后重试"})
    assert retried.status_code == 200
    assert retried.json()["data"]["status"] == "pending"
    assert retried.json()["data"]["retry_count"] == 1

    cancelled = client.post(f"/api/tasks/{task_id}/cancel", json={"reason": "项目已暂停"})
    assert cancelled.status_code == 200
    assert cancelled.json()["data"]["status"] == "cancelled"
