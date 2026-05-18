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
    )


def test_create_project_returns_active_init_project():
    client = make_client()

    response = create_project(client)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["name"] == "用户登录功能"
    assert body["data"]["status"] == "active"
    assert body["data"]["current_phase"] == "INIT"
    assert body["data"]["id"].startswith("proj_")
    assert "request_id" in body


def test_get_project_returns_project_detail():
    client = make_client()
    project_id = create_project(client).json()["data"]["id"]

    response = client.get(f"/api/projects/{project_id}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == project_id
    assert data["owner_user_id"] == "feishu_user_001"
    assert data["repo_url"] == "https://github.com/example/app"
    assert data["status"] == "active"
    assert data["current_phase"] == "INIT"
    assert "created_at" in data
    assert "updated_at" in data


def test_project_status_lifecycle_actions():
    client = make_client()
    project_id = create_project(client).json()["data"]["id"]

    paused = client.post(f"/api/projects/{project_id}/pause", json={"reason": "等待用户确认设计变更"})
    assert paused.status_code == 200
    assert paused.json()["data"]["status"] == "paused"

    status = client.get(f"/api/projects/{project_id}/status")
    assert status.status_code == 200
    assert status.json()["data"]["project_id"] == project_id
    assert status.json()["data"]["status"] == "paused"
    assert status.json()["data"]["risks"] == []
    assert status.json()["data"]["pending_user_actions"] == []

    resumed = client.post(f"/api/projects/{project_id}/resume", json={"reason": "用户已确认继续推进"})
    assert resumed.status_code == 200
    assert resumed.json()["data"]["status"] == "active"

    cancelled = client.post(f"/api/projects/{project_id}/cancel", json={"reason": "用户决定终止当前需求"})
    assert cancelled.status_code == 200
    assert cancelled.json()["data"]["status"] == "cancelled"


def test_list_project_events_includes_project_created_event():
    client = make_client()
    project_id = create_project(client).json()["data"]["id"]

    response = client.get(f"/api/projects/{project_id}/events")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    events = body["data"]
    assert len(events) >= 1
    assert events[0]["project_id"] == project_id
    assert events[0]["event_type"] == "project_created"
    assert events[0]["actor_type"] == "system"
    assert events[0]["actor_id"] == "api"
    assert events[0]["payload"] == {"reason": "需要实现登录功能"}
    assert "request_id" in body


def test_list_project_events_filters_workflow_events():
    client = make_client()
    project_id = create_project(client).json()["data"]["id"]
    client.post(
        f"/api/projects/{project_id}/workflow/advance",
        json={
            "from_phase": "INIT",
            "to_phase": "REQUIREMENT_DISCUSSION",
            "reason": "进入需求讨论",
            "evidence": ["artifact_requirement_notes"],
        },
    )

    response = client.get(f"/api/projects/{project_id}/events", params={"event_type": "workflow_advanced"})

    assert response.status_code == 200
    events = response.json()["data"]
    assert len(events) == 1
    assert events[0]["event_type"] == "workflow_advanced"
    assert events[0]["actor_id"] == "workflow"
    assert events[0]["payload"]["from_phase"] == "INIT"
    assert events[0]["payload"]["to_phase"] == "REQUIREMENT_DISCUSSION"
    assert events[0]["payload"]["reason"] == "进入需求讨论"
    assert events[0]["payload"]["evidence"] == ["artifact_requirement_notes"]


def test_list_project_events_includes_lifecycle_action_reasons():
    client = make_client()
    project_id = create_project(client).json()["data"]["id"]
    client.post(f"/api/projects/{project_id}/pause", json={"reason": "等待用户确认设计变更"})
    client.post(f"/api/projects/{project_id}/resume", json={"reason": "用户已确认继续推进"})
    client.post(f"/api/projects/{project_id}/cancel", json={"reason": "用户决定终止当前需求"})

    response = client.get(f"/api/projects/{project_id}/events")

    assert response.status_code == 200
    events_by_type = {event["event_type"]: event for event in response.json()["data"]}
    assert events_by_type["project_paused"]["payload"] == {"reason": "等待用户确认设计变更"}
    assert events_by_type["project_resumed"]["payload"] == {"reason": "用户已确认继续推进"}
    assert events_by_type["project_cancelled"]["payload"] == {"reason": "用户决定终止当前需求"}
