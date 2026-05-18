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


def create_review(client, project_id):
    return client.post(
        f"/api/projects/{project_id}/reviews",
        json={
            "type": "design_review",
            "phase": "DESIGN_REVIEW",
            "owner_agent": "ARCH",
            "participants": ["PM", "PDM", "DEV", "TEST", "SEC"],
            "input_artifacts": ["artifact_detail_design_draft", "artifact_api_design"],
        },
    )


def test_create_review_returns_open_review():
    client = make_client()
    project_id = create_project(client)

    response = create_review(client, project_id)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["id"].startswith("review_")
    assert body["data"]["status"] == "open"
    assert body["data"]["round"] == 1
    assert body["data"]["participants"] == ["PM", "PDM", "DEV", "TEST", "SEC"]
    assert "request_id" in body


def test_list_and_get_reviews():
    client = make_client()
    project_id = create_project(client)
    review_id = create_review(client, project_id).json()["data"]["id"]

    list_response = client.get(f"/api/projects/{project_id}/reviews")
    get_response = client.get(f"/api/reviews/{review_id}")

    assert list_response.status_code == 200
    assert list_response.json()["data"][0]["id"] == review_id
    assert get_response.status_code == 200
    assert get_response.json()["data"]["id"] == review_id
    assert get_response.json()["data"]["input_artifacts"] == ["artifact_detail_design_draft", "artifact_api_design"]


def test_add_review_comment_and_complete_review():
    client = make_client()
    project_id = create_project(client)
    review_id = create_review(client, project_id).json()["data"]["id"]

    comment = client.post(
        f"/api/reviews/{review_id}/comments",
        json={
            "reviewer_agent": "SEC",
            "status": "fail",
            "severity": "major",
            "comment": "当前设计没有说明 token 过期策略",
            "required_change": "补充 token 过期、刷新和失效策略",
            "related_artifact": "artifact_detail_design_draft",
        },
    )
    assert comment.status_code == 200
    assert comment.json()["data"]["id"].startswith("comment_")
    assert comment.json()["data"]["reviewer_agent"] == "SEC"
    assert comment.json()["data"]["severity"] == "major"

    completed = client.post(
        f"/api/reviews/{review_id}/complete",
        json={"conclusion": "failed", "summary": "设计评审未通过，需要补充 token 策略。"},
    )
    assert completed.status_code == 200
    assert completed.json()["data"]["status"] == "failed"
    assert completed.json()["data"]["conclusion"] == "failed"
    assert completed.json()["data"]["completed_at"] is not None


def advance(client, project_id, from_phase, to_phase):
    return client.post(
        f"/api/projects/{project_id}/workflow/advance",
        json={
            "from_phase": from_phase,
            "to_phase": to_phase,
            "reason": "阶段推进",
            "evidence": [],
        },
    )


def advance_to_requirement_review(client, project_id):
    advance(client, project_id, "INIT", "REQUIREMENT_DISCUSSION")
    advance(client, project_id, "REQUIREMENT_DISCUSSION", "REQUIREMENT_REVIEW")


def advance_to_design_review(client, project_id):
    advance_to_requirement_review(client, project_id)
    advance(client, project_id, "REQUIREMENT_REVIEW", "REQUIREMENT_APPROVED")
    advance(client, project_id, "REQUIREMENT_APPROVED", "DESIGN_AND_TESTCASE_DRAFTING")
    advance(client, project_id, "DESIGN_AND_TESTCASE_DRAFTING", "DESIGN_REVIEW")


def create_review_with(client, project_id, review_type, phase):
    return client.post(
        f"/api/projects/{project_id}/reviews",
        json={
            "type": review_type,
            "phase": phase,
            "owner_agent": "ARCH",
            "participants": ["PM", "PDM", "DEV", "TEST", "SEC"],
            "input_artifacts": ["artifact_detail_design_draft"],
        },
    )


def complete_review(client, review_id, conclusion):
    return client.post(
        f"/api/reviews/{review_id}/complete",
        json={"conclusion": conclusion, "summary": "评审完成"},
    )


def test_evaluate_passed_design_review_advances_workflow_to_development():
    client = make_client()
    project_id = create_project(client)
    advance_to_design_review(client, project_id)
    review_id = create_review_with(client, project_id, "design_review", "DESIGN_REVIEW").json()["data"]["id"]
    complete_review(client, review_id, "passed")

    response = client.post(f"/api/reviews/{review_id}/evaluate-gate")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["review_id"] == review_id
    assert data["project_id"] == project_id
    assert data["from_phase"] == "DESIGN_REVIEW"
    assert data["to_phase"] == "DEVELOPMENT"
    assert data["conclusion"] == "passed"
    assert data["workflow"]["current_phase"] == "DEVELOPMENT"
    workflow = client.get(f"/api/projects/{project_id}/workflow")
    assert workflow.json()["data"]["current_phase"] == "DEVELOPMENT"


def test_evaluate_failed_requirement_review_rejects_to_revision():
    client = make_client()
    project_id = create_project(client)
    advance_to_requirement_review(client, project_id)
    review_id = create_review_with(client, project_id, "requirement_review", "REQUIREMENT_REVIEW").json()["data"]["id"]
    complete_review(client, review_id, "failed")

    response = client.post(f"/api/reviews/{review_id}/evaluate-gate")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["from_phase"] == "REQUIREMENT_REVIEW"
    assert data["to_phase"] == "REQUIREMENT_REVISION"
    assert data["conclusion"] == "failed"
    assert data["workflow"]["current_phase"] == "REQUIREMENT_REVISION"


def test_evaluate_open_review_returns_400():
    client = make_client()
    project_id = create_project(client)
    advance_to_design_review(client, project_id)
    review_id = create_review_with(client, project_id, "design_review", "DESIGN_REVIEW").json()["data"]["id"]

    response = client.post(f"/api/reviews/{review_id}/evaluate-gate")

    assert response.status_code == 400


def test_evaluate_review_gate_rejects_phase_mismatch():
    client = make_client()
    project_id = create_project(client)
    review_id = create_review_with(client, project_id, "design_review", "DESIGN_REVIEW").json()["data"]["id"]
    complete_review(client, review_id, "passed")

    response = client.post(f"/api/reviews/{review_id}/evaluate-gate")

    assert response.status_code == 400
    workflow = client.get(f"/api/projects/{project_id}/workflow")
    assert workflow.json()["data"]["current_phase"] == "INIT"
