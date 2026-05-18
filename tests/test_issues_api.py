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
            "name": "缺陷管理项目",
            "description": "验证测试、安全、验收问题闭环",
            "owner_user_id": "feishu_user_001",
            "repo_url": "https://github.com/example/app",
            "default_branch": "main",
            "initial_requirement": "需要记录测试失败问题",
        },
    ).json()["data"]["id"]


def create_issue(client, project_id, **overrides):
    payload = {
        "source": "test",
        "phase": "TEST_AND_SECURITY_VALIDATION",
        "title": "登录失败提示不符合预期",
        "description": "错误密码登录时提示文案不符合测试清单",
        "severity": "major",
        "priority": "high",
        "assigned_agent": "DEV",
        "related_artifacts": ["artifact_test_checklist"],
        "reproduce_steps": ["输入错误密码", "点击登录"],
        "expected_result": "提示账号或密码错误",
        "actual_result": "提示系统异常",
        "max_retries": 3,
    }
    payload.update(overrides)
    return client.post(f"/api/projects/{project_id}/issues", json=payload)


def test_create_and_get_issue():
    client = make_client()
    project_id = create_project(client)

    created = create_issue(client, project_id)

    assert created.status_code == 200
    body = created.json()
    assert body["success"] is True
    assert body["data"]["id"].startswith("issue_")
    assert body["data"]["status"] == "open"
    assert "request_id" in body

    detail = client.get(f"/api/issues/{body['data']['id']}")

    assert detail.status_code == 200
    data = detail.json()["data"]
    assert data["project_id"] == project_id
    assert data["source"] == "test"
    assert data["phase"] == "TEST_AND_SECURITY_VALIDATION"
    assert data["title"] == "登录失败提示不符合预期"
    assert data["severity"] == "major"
    assert data["priority"] == "high"
    assert data["assigned_agent"] == "DEV"
    assert data["related_artifacts"] == ["artifact_test_checklist"]
    assert data["reproduce_steps"] == ["输入错误密码", "点击登录"]
    assert data["expected_result"] == "提示账号或密码错误"
    assert data["actual_result"] == "提示系统异常"


def test_list_issues_filters_by_source_severity_assignee_and_status():
    client = make_client()
    project_id = create_project(client)
    create_issue(client, project_id, title="登录失败提示不符合预期")
    create_issue(
        client,
        project_id,
        source="security",
        title="Token 未设置过期时间",
        severity="critical",
        assigned_agent="DEV",
        related_artifacts=["artifact_security_report"],
    )

    response = client.get(
        f"/api/projects/{project_id}/issues",
        params={"source": "security", "severity": "critical", "assigned_agent": "DEV", "status": "open"},
    )

    assert response.status_code == 200
    issues = response.json()["data"]
    assert len(issues) == 1
    assert issues[0]["title"] == "Token 未设置过期时间"
    assert issues[0]["source"] == "security"
    assert issues[0]["severity"] == "critical"


def test_assign_and_update_issue_status():
    client = make_client()
    project_id = create_project(client)
    issue_id = create_issue(client, project_id, assigned_agent=None).json()["data"]["id"]

    assigned = client.post(f"/api/issues/{issue_id}/assign", json={"assigned_agent": "DEV"})

    assert assigned.status_code == 200
    assert assigned.json()["data"]["assigned_agent"] == "DEV"
    assert assigned.json()["data"]["status"] == "assigned"

    fixed = client.post(f"/api/issues/{issue_id}/status", json={"status": "fixed", "reason": "已修复"})
    assert fixed.status_code == 200
    assert fixed.json()["data"]["status"] == "fixed"
    assert fixed.json()["data"]["retry_count"] == 0

    reopened = client.post(f"/api/issues/{issue_id}/status", json={"status": "reopened", "reason": "回归仍失败"})
    assert reopened.status_code == 200
    assert reopened.json()["data"]["status"] == "reopened"
    assert reopened.json()["data"]["retry_count"] == 1


def test_reopened_issue_at_retry_threshold_creates_escalation():
    client = make_client()
    project_id = create_project(client)
    issue_id = create_issue(client, project_id, max_retries=3).json()["data"]["id"]

    first = client.post(f"/api/issues/{issue_id}/status", json={"status": "reopened", "reason": "第一轮验证失败"})
    second = client.post(f"/api/issues/{issue_id}/status", json={"status": "reopened", "reason": "第二轮验证失败"})
    third = client.post(f"/api/issues/{issue_id}/status", json={"status": "reopened", "reason": "第三轮验证失败"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 200
    assert third.json()["data"]["retry_count"] == 3
    escalations = client.get(f"/api/projects/{project_id}/escalations")
    assert escalations.status_code == 200
    data = escalations.json()["data"]
    assert len(data) == 1
    assert data[0]["type"] == "issue_retry_threshold"
    assert data[0]["phase"] == "TEST_AND_SECURITY_VALIDATION"
    assert data[0]["source_agent"] == "DEV"
    assert data[0]["retry_count"] == 3
    assert data[0]["threshold"] == 3
