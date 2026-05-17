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


def create_task(client, project_id):
    return client.post(
        f"/api/projects/{project_id}/tasks",
        json={
            "phase": "DEVELOPMENT",
            "owner_agent": "DEV",
            "title": "实现登录接口",
            "description": "根据 PRD 和详细设计实现登录接口",
            "input_artifacts": ["artifact_prd_final"],
            "expected_artifacts": ["source_code_diff"],
            "max_retries": 3,
        },
    ).json()["data"]["id"]


def create_artifact(client, project_id, task_id, artifact_type="design_doc", created_by="ARCH"):
    return client.post(
        f"/api/projects/{project_id}/artifacts",
        json={
            "task_id": task_id,
            "artifact_type": artifact_type,
            "name": "detail-design-final.md",
            "path": "docs/design/detail-design-final.md",
            "version": "v1",
            "created_by": created_by,
            "metadata": {"phase": "DESIGN_REVIEW"},
        },
    )


def test_create_artifact_registers_project_artifact():
    client = make_client()
    project_id = create_project(client)
    task_id = create_task(client, project_id)

    response = create_artifact(client, project_id, task_id)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["id"].startswith("artifact_")
    assert body["data"]["status"] == "active"
    assert body["data"]["metadata"] == {"phase": "DESIGN_REVIEW"}
    assert "request_id" in body


def test_list_artifacts_filters_and_get_artifact_returns_metadata():
    client = make_client()
    project_id = create_project(client)
    task_id = create_task(client, project_id)
    artifact_id = create_artifact(client, project_id, task_id).json()["data"]["id"]
    create_artifact(client, project_id, task_id, artifact_type="security_report", created_by="SEC")

    listed = client.get(
        f"/api/projects/{project_id}/artifacts",
        params={"artifact_type": "design_doc", "created_by": "ARCH", "status": "active"},
    )
    detail = client.get(f"/api/artifacts/{artifact_id}")

    assert listed.status_code == 200
    assert len(listed.json()["data"]) == 1
    assert listed.json()["data"][0]["id"] == artifact_id
    assert detail.status_code == 200
    assert detail.json()["data"]["id"] == artifact_id
    assert detail.json()["data"]["metadata"] == {"phase": "DESIGN_REVIEW"}
