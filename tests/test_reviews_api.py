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
