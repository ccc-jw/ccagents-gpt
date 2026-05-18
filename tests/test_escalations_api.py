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


def create_escalation(client, project_id):
    return client.post(
        f"/api/projects/{project_id}/escalations",
        json={
            "type": "review_failed_threshold",
            "phase": "DESIGN_REVIEW",
            "source_agent": "PM",
            "target_user_id": "feishu_user_001",
            "retry_count": 3,
            "threshold": 3,
            "summary": "设计评审连续 3 次未通过，需要用户决策。",
            "options": ["continue", "redesign", "manual", "cancel", "change_requirement"],
        },
    )


def test_create_escalation_defaults_to_pending_user_decision():
    client = make_client()
    project_id = create_project(client)

    response = create_escalation(client, project_id)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["id"].startswith("esc_")
    assert body["data"]["status"] == "pending_user_decision"
    assert body["data"]["threshold"] == 3
    assert body["data"]["options"] == ["continue", "redesign", "manual", "cancel", "change_requirement"]
    assert "request_id" in body


def test_list_get_and_decide_escalation():
    client = make_client()
    project_id = create_project(client)
    escalation_id = create_escalation(client, project_id).json()["data"]["id"]

    listed = client.get(f"/api/projects/{project_id}/escalations")
    detail = client.get(f"/api/escalations/{escalation_id}")
    decided = client.post(
        f"/api/escalations/{escalation_id}/decision",
        json={"decision": "continue", "comment": "再自动修复一轮"},
    )

    assert listed.status_code == 200
    assert listed.json()["data"][0]["id"] == escalation_id
    assert detail.status_code == 200
    assert detail.json()["data"]["id"] == escalation_id
    assert decided.status_code == 200
    assert decided.json()["data"]["status"] == "decided"
    assert decided.json()["data"]["decision"] == "continue"
    assert decided.json()["data"]["decision_comment"] == "再自动修复一轮"
    assert decided.json()["data"]["decided_at"] is not None


def test_create_escalation_records_project_event():
    client = make_client()
    project_id = create_project(client)

    response = create_escalation(client, project_id)
    events = client.get(f"/api/projects/{project_id}/events", params={"event_type": "escalation_created"}).json()["data"]

    assert response.status_code == 200
    assert len(events) == 1
    payload = events[0]["payload"]
    assert payload["escalation_id"] == response.json()["data"]["id"]
    assert payload["type"] == "review_failed_threshold"
    assert payload["phase"] == "DESIGN_REVIEW"
    assert payload["source_agent"] == "PM"
    assert payload["target_user_id"] == "feishu_user_001"
    assert payload["status"] == "pending_user_decision"
    assert payload["retry_count"] == 3
    assert payload["threshold"] == 3


def test_decide_escalation_records_project_event():
    client = make_client()
    project_id = create_project(client)
    escalation_id = create_escalation(client, project_id).json()["data"]["id"]

    response = client.post(
        f"/api/escalations/{escalation_id}/decision",
        json={"decision": "continue", "comment": "再自动修复一轮"},
    )
    events = client.get(f"/api/projects/{project_id}/events", params={"event_type": "escalation_decided"}).json()["data"]

    assert response.status_code == 200
    assert len(events) == 1
    payload = events[0]["payload"]
    assert payload["escalation_id"] == escalation_id
    assert payload["status"] == "decided"
    assert payload["decision"] == "continue"
    assert payload["decision_comment"] == "再自动修复一轮"
