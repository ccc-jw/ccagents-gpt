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


def advance(client, project_id, from_phase, to_phase):
    return client.post(
        f"/api/projects/{project_id}/workflow/advance",
        json={
            "from_phase": from_phase,
            "to_phase": to_phase,
            "reason": "阶段推进",
            "evidence": ["review_001"],
        },
    )


def test_get_workflow_returns_current_phase_and_allowed_transitions():
    client = make_client()
    project_id = create_project(client)

    response = client.get(f"/api/projects/{project_id}/workflow")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["project_id"] == project_id
    assert body["data"]["current_phase"] == "INIT"
    assert "REQUIREMENT_DISCUSSION" in body["data"]["allowed_transitions"]
    assert "request_id" in body


def test_advance_workflow_updates_project_phase():
    client = make_client()
    project_id = create_project(client)

    response = advance(client, project_id, "INIT", "REQUIREMENT_DISCUSSION")

    assert response.status_code == 200
    assert response.json()["data"]["current_phase"] == "REQUIREMENT_DISCUSSION"
    workflow = client.get(f"/api/projects/{project_id}/workflow")
    assert workflow.json()["data"]["current_phase"] == "REQUIREMENT_DISCUSSION"


def test_advance_rejects_mismatched_from_phase_and_invalid_transition():
    client = make_client()
    project_id = create_project(client)

    mismatched = advance(client, project_id, "REQUIREMENT_REVIEW", "REQUIREMENT_APPROVED")
    assert mismatched.status_code == 400

    invalid = advance(client, project_id, "INIT", "PRODUCT_ACCEPTANCE")
    assert invalid.status_code == 400

    workflow = client.get(f"/api/projects/{project_id}/workflow")
    assert workflow.json()["data"]["current_phase"] == "INIT"


def test_reject_workflow_updates_to_revision_phase():
    client = make_client()
    project_id = create_project(client)
    advance(client, project_id, "INIT", "REQUIREMENT_DISCUSSION")
    advance(client, project_id, "REQUIREMENT_DISCUSSION", "REQUIREMENT_REVIEW")

    response = client.post(
        f"/api/projects/{project_id}/workflow/reject",
        json={
            "from_phase": "REQUIREMENT_REVIEW",
            "to_phase": "REQUIREMENT_REVISION",
            "reason": "需求评审未通过",
            "evidence": ["review_002"],
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["current_phase"] == "REQUIREMENT_REVISION"


def test_reject_workflow_rejects_invalid_target():
    client = make_client()
    project_id = create_project(client)

    response = client.post(
        f"/api/projects/{project_id}/workflow/reject",
        json={
            "from_phase": "INIT",
            "to_phase": "DONE",
            "reason": "非法回退",
            "evidence": [],
        },
    )

    assert response.status_code == 400


def test_transition_workflow_updates_phase_with_generic_endpoint():
    client = make_client()
    project_id = create_project(client)

    response = client.post(
        f"/api/projects/{project_id}/workflow/transition",
        json={
            "from_phase": "INIT",
            "to_phase": "REQUIREMENT_DISCUSSION",
            "reason": "开始需求沟通",
            "evidence": ["msg_001"],
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["current_phase"] == "REQUIREMENT_DISCUSSION"
    events = client.get(f"/api/projects/{project_id}/events", params={"event_type": "workflow_transitioned"})
    assert events.json()["data"][0]["payload"] == {
        "from_phase": "INIT",
        "to_phase": "REQUIREMENT_DISCUSSION",
        "reason": "开始需求沟通",
        "evidence": ["msg_001"],
    }
