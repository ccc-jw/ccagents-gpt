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
