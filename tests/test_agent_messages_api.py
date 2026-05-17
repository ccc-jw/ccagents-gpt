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


def create_message(client, project_id, from_agent="DEV", to_agent="PDM", message_type="requirement_question"):
    return client.post(
        f"/api/projects/{project_id}/agent-messages",
        json={
            "from_agent": from_agent,
            "to_agent": to_agent,
            "message_type": message_type,
            "phase": "DEVELOPMENT",
            "title": "登录失败是否需要区分账号不存在和密码错误",
            "content": "PRD 当前只说明登录失败返回错误提示，未明确是否需要区分账号不存在和密码错误。",
            "related_artifacts": ["artifact_prd_final"],
        },
    )


def test_create_agent_message_defaults_to_pending():
    client = make_client()
    project_id = create_project(client)

    response = create_message(client, project_id)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["id"].startswith("msg_")
    assert body["data"]["status"] == "pending"
    assert body["data"]["related_artifacts"] == ["artifact_prd_final"]
    assert "request_id" in body


def test_list_messages_filters_and_get_message_returns_related_artifacts():
    client = make_client()
    project_id = create_project(client)
    message_id = create_message(client, project_id).json()["data"]["id"]
    create_message(client, project_id, from_agent="SEC", to_agent="DEV", message_type="security_question")

    listed = client.get(
        f"/api/projects/{project_id}/agent-messages",
        params={
            "to_agent": "PDM",
            "from_agent": "DEV",
            "message_type": "requirement_question",
            "status": "pending",
        },
    )
    detail = client.get(f"/api/agent-messages/{message_id}")

    assert listed.status_code == 200
    assert len(listed.json()["data"]) == 1
    assert listed.json()["data"][0]["id"] == message_id
    assert detail.status_code == 200
    assert detail.json()["data"]["id"] == message_id
    assert detail.json()["data"]["related_artifacts"] == ["artifact_prd_final"]


def test_update_message_status():
    client = make_client()
    project_id = create_project(client)
    message_id = create_message(client, project_id).json()["data"]["id"]

    response = client.post(f"/api/agent-messages/{message_id}/status", json={"status": "resolved"})
    detail = client.get(f"/api/agent-messages/{message_id}")

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "resolved"
    assert detail.json()["data"]["status"] == "resolved"
