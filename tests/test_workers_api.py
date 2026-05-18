import tempfile

from fastapi.testclient import TestClient

from app.main import create_app


def make_client():
    database = tempfile.NamedTemporaryFile(delete=False)
    return TestClient(create_app(database.name))


def create_project(client, name="自动执行项目"):
    return client.post(
        "/api/projects",
        json={
            "name": name,
            "description": "验证 worker tick",
            "owner_user_id": "feishu_user_001",
            "repo_url": "https://github.com/example/app",
            "default_branch": "main",
            "initial_requirement": "需要 worker 自动推进任务",
        },
    ).json()["data"]["id"]


def create_task(client, project_id):
    return client.post(
        f"/api/projects/{project_id}/tasks",
        json={
            "phase": "DEVELOPMENT",
            "owner_agent": "DEV",
            "title": "实现 worker 推进",
            "description": "执行 worker tick 调度任务",
            "input_artifacts": [],
            "expected_artifacts": ["runner_result"],
            "max_retries": 3,
        },
    ).json()["data"]["id"]


def test_worker_tick_dispatches_one_task_for_active_project():
    client = make_client()
    project_id = create_project(client)
    task_id = create_task(client, project_id)

    response = client.post("/api/workers/tick", json={"runner_type": "claude_code_cli", "workspace_strategy": "git_worktree"})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["action"] == "project_ticked"
    assert data["project_id"] == project_id
    assert data["tick"]["action"] == "dispatched_task"
    assert data["tick"]["dispatch"]["task_id"] == task_id
    assert client.get(f"/api/tasks/{task_id}").json()["data"]["status"] == "running"


def test_worker_tick_returns_idle_when_no_active_pending_work():
    client = make_client()

    response = client.post("/api/workers/tick", json={})

    assert response.status_code == 200
    assert response.json()["data"] == {"action": "idle", "message": "没有可自动推进的项目。"}


def test_worker_tick_skips_paused_and_cancelled_projects():
    client = make_client()
    paused_project_id = create_project(client, "暂停项目")
    cancelled_project_id = create_project(client, "取消项目")
    paused_task_id = create_task(client, paused_project_id)
    cancelled_task_id = create_task(client, cancelled_project_id)
    client.post(f"/api/projects/{paused_project_id}/pause", json={"reason": "暂停"})
    client.post(f"/api/projects/{cancelled_project_id}/cancel", json={"reason": "取消"})

    response = client.post("/api/workers/tick", json={})

    assert response.status_code == 200
    assert response.json()["data"] == {"action": "idle", "message": "没有可自动推进的项目。"}
    assert client.get(f"/api/tasks/{paused_task_id}").json()["data"]["status"] == "pending"
    assert client.get(f"/api/tasks/{cancelled_task_id}").json()["data"]["status"] == "pending"


def test_worker_tick_records_project_event():
    client = make_client()
    project_id = create_project(client)
    task_id = create_task(client, project_id)

    response = client.post("/api/workers/tick", json={})
    events = client.get(f"/api/projects/{project_id}/events", params={"event_type": "worker_tick"}).json()["data"]

    assert response.status_code == 200
    assert len(events) == 1
    payload = events[0]["payload"]
    assert payload["action"] == "project_ticked"
    assert payload["task_id"] == task_id
    assert payload["task_run_id"] == response.json()["data"]["tick"]["dispatch"]["task_run_id"]
