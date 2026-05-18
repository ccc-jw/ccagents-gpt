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
            "name": "自动执行项目",
            "description": "验证自动推进 tick",
            "owner_user_id": "feishu_user_001",
            "repo_url": "https://github.com/example/app",
            "default_branch": "main",
            "initial_requirement": "需要自动推进任务执行",
        },
    ).json()["data"]["id"]


def create_task(client, project_id):
    return client.post(
        f"/api/projects/{project_id}/tasks",
        json={
            "phase": "DEVELOPMENT",
            "owner_agent": "DEV",
            "title": "实现自动推进",
            "description": "执行一个自动推进任务",
            "input_artifacts": ["artifact_design"],
            "expected_artifacts": ["runner_result"],
            "max_retries": 3,
        },
    ).json()["data"]["id"]


def test_automation_tick_dispatches_next_task_and_returns_execution_plan():
    client = make_client()
    project_id = create_project(client)
    task_id = create_task(client, project_id)

    response = client.post(
        f"/api/projects/{project_id}/automation/tick",
        json={"runner_type": "claude_code_cli", "workspace_strategy": "git_worktree"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["project_id"] == project_id
    assert data["action"] == "dispatched_task"
    assert data["dispatch"]["task_id"] == task_id
    assert data["dispatch"]["task_run_id"].startswith("run_")
    assert data["execution_plan"]["task_run_id"] == data["dispatch"]["task_run_id"]
    assert data["execution_plan"]["command"][-1] == "执行一个自动推进任务"
    assert client.get(f"/api/tasks/{task_id}").json()["data"]["status"] == "running"


def test_automation_tick_records_project_event():
    client = make_client()
    project_id = create_project(client)
    task_id = create_task(client, project_id)

    response = client.post(f"/api/projects/{project_id}/automation/tick", json={})
    events = client.get(f"/api/projects/{project_id}/events", params={"event_type": "automation_tick"}).json()["data"]

    assert response.status_code == 200
    assert len(events) == 1
    payload = events[0]["payload"]
    assert payload["action"] == "dispatched_task"
    assert payload["task_id"] == task_id
    assert payload["task_run_id"] == response.json()["data"]["dispatch"]["task_run_id"]


def test_automation_tick_returns_idle_when_no_pending_tasks():
    client = make_client()
    project_id = create_project(client)

    response = client.post(f"/api/projects/{project_id}/automation/tick", json={})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data == {
        "project_id": project_id,
        "action": "idle",
        "dispatch": {"dispatched": False, "message": "没有匹配的待调度任务。"},
        "execution_plan": None,
    }
