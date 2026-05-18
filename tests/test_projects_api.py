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


def test_list_projects_filters_by_owner_and_status():
    client = make_client()
    first_id = create_project(client).json()["data"]["id"]
    second_id = client.post(
        "/api/projects",
        json={
            "name": "支付功能",
            "description": "实现支付流程",
            "owner_user_id": "feishu_user_002",
            "repo_url": "https://github.com/example/app",
            "default_branch": "main",
            "initial_requirement": "需要实现支付功能",
        },
    ).json()["data"]["id"]
    client.post(f"/api/projects/{second_id}/pause", json={"reason": "等待用户确认"})

    all_projects = client.get("/api/projects")
    filtered = client.get("/api/projects", params={"owner_user_id": "feishu_user_002", "status": "paused"})

    assert all_projects.status_code == 200
    assert {project["id"] for project in all_projects.json()["data"]} == {first_id, second_id}
    assert filtered.status_code == 200
    assert [project["id"] for project in filtered.json()["data"]] == [second_id]
    assert filtered.json()["data"][0]["status"] == "paused"


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


def test_project_status_includes_progress_risks_and_pending_actions():
    client = make_client()
    project_id = create_project(client).json()["data"]["id"]
    first_task = client.post(
        f"/api/projects/{project_id}/tasks",
        json={
            "phase": "DEVELOPMENT",
            "owner_agent": "DEV",
            "title": "实现登录接口",
            "description": "根据 PRD 和详细设计实现登录接口",
            "input_artifacts": [],
            "expected_artifacts": [],
            "max_retries": 3,
        },
    ).json()["data"]["id"]
    second_task = client.post(
        f"/api/projects/{project_id}/tasks",
        json={
            "phase": "DEVELOPMENT",
            "owner_agent": "TEST",
            "title": "验证登录接口",
            "description": "执行测试清单",
            "input_artifacts": [],
            "expected_artifacts": [],
            "max_retries": 3,
        },
    ).json()["data"]["id"]
    client.post(f"/api/tasks/{first_task}/start", json={"runner_type": "claude_code_cli"})
    client.post(f"/api/tasks/{second_task}/cancel", json={"reason": "暂不执行"})
    client.post(
        f"/api/projects/{project_id}/issues",
        json={
            "source": "security",
            "phase": "TEST_AND_SECURITY_VALIDATION",
            "title": "Token 未设置过期时间",
            "description": "安全检查发现 token 未设置过期时间",
            "severity": "critical",
            "priority": "high",
            "assigned_agent": "DEV",
            "related_artifacts": [],
            "reproduce_steps": [],
            "expected_result": "Token 有明确过期时间",
            "actual_result": "Token 永不过期",
            "max_retries": 3,
        },
    )
    client.post(
        f"/api/projects/{project_id}/escalations",
        json={
            "type": "issue_retry_threshold",
            "phase": "TEST_AND_SECURITY_VALIDATION",
            "source_agent": "DEV",
            "target_user_id": "feishu_user_001",
            "retry_count": 3,
            "threshold": 3,
            "summary": "问题连续重开 3 次，需要用户决策。",
            "options": ["continue", "manual", "cancel"],
        },
    )

    response = client.get(f"/api/projects/{project_id}/status")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["progress_summary"] == "任务 2 个：pending 0，running 1，completed 0，failed 0，cancelled 1。"
    assert data["risks"] == ["存在 1 个 critical 未关闭问题。"]
    assert data["pending_user_actions"] == ["问题连续重开 3 次，需要用户决策。"]
