import tempfile

from fastapi.testclient import TestClient

from app.main import create_app


def make_client():
    database = tempfile.NamedTemporaryFile(delete=False)
    return TestClient(create_app(database.name))


def post_event(client, text):
    return client.post(
        "/api/feishu/events",
        json={
            "event_type": "message",
            "message_type": "text",
            "chat_id": "chat_001",
            "user_id": "feishu_user_001",
            "text": text,
        },
    )


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
            "type": "issue_retry_threshold",
            "phase": "TEST_AND_SECURITY_VALIDATION",
            "source_agent": "PM",
            "target_user_id": "feishu_user_001",
            "retry_count": 3,
            "threshold": 3,
            "summary": "问题连续 3 次验证失败，需要用户决策。",
            "options": ["continue", "manual", "cancel"],
        },
    ).json()["data"]["id"]


def test_receive_feishu_message_event_parses_status_command():
    client = make_client()

    response = post_event(client, "/status proj_001")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["accepted"] is True
    assert body["data"]["source"] == "feishu"
    assert body["data"]["event_type"] == "message"
    assert body["data"]["message_type"] == "text"
    assert body["data"]["chat_id"] == "chat_001"
    assert body["data"]["user_id"] == "feishu_user_001"
    assert body["data"]["text"] == "/status proj_001"
    assert body["data"]["command"] == "status"
    assert body["data"]["args"] == ["proj_001"]
    assert "request_id" in body


def test_receive_feishu_message_event_accepts_plain_text():
    client = make_client()

    response = post_event(client, "项目现在进展怎么样")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["accepted"] is True
    assert data["text"] == "项目现在进展怎么样"
    assert data["command"] is None
    assert data["args"] == []


def test_status_command_returns_project_status_summary():
    client = make_client()
    project_id = create_project(client)

    response = post_event(client, f"/status {project_id}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["command"] == "status"
    assert data["handled"] is True
    assert data["project_status"] == {
        "project_id": project_id,
        "current_phase": "INIT",
        "status": "active",
        "progress_summary": "项目当前处于 INIT 阶段。",
        "risks": [],
        "pending_user_actions": [],
    }
    assert data["reply_text"] == "项目当前处于 INIT 阶段。"


def test_pause_and_resume_commands_update_project_status():
    client = make_client()
    project_id = create_project(client)

    paused = post_event(client, f"/pause {project_id}")
    paused_status = client.get(f"/api/projects/{project_id}/status")
    resumed = post_event(client, f"/resume {project_id}")
    resumed_status = client.get(f"/api/projects/{project_id}/status")

    assert paused.status_code == 200
    assert paused.json()["data"]["handled"] is True
    assert paused.json()["data"]["project_status"]["status"] == "paused"
    assert paused.json()["data"]["reply_text"] == "项目已暂停。"
    assert paused_status.json()["data"]["status"] == "paused"
    assert resumed.status_code == 200
    assert resumed.json()["data"]["handled"] is True
    assert resumed.json()["data"]["project_status"]["status"] == "active"
    assert resumed.json()["data"]["reply_text"] == "项目已恢复。"
    assert resumed_status.json()["data"]["status"] == "active"


def test_cancel_command_updates_project_status():
    client = make_client()
    project_id = create_project(client)

    cancelled = post_event(client, f"/cancel {project_id}")
    status = client.get(f"/api/projects/{project_id}/status")

    assert cancelled.status_code == 200
    assert cancelled.json()["data"]["handled"] is True
    assert cancelled.json()["data"]["project_status"]["status"] == "cancelled"
    assert cancelled.json()["data"]["reply_text"] == "项目已取消。"
    assert status.json()["data"]["status"] == "cancelled"


def test_parse_supported_feishu_slash_commands():
    client = make_client()

    help_response = post_event(client, "/help")
    pause_response = post_event(client, "/pause proj_001")
    resume_response = post_event(client, "/resume proj_001")
    cancel_response = post_event(client, "/cancel proj_001")

    assert help_response.json()["data"]["command"] == "help"
    assert help_response.json()["data"]["args"] == []
    assert pause_response.json()["data"]["command"] == "pause"
    assert pause_response.json()["data"]["args"] == ["proj_001"]
    assert resume_response.json()["data"]["command"] == "resume"
    assert resume_response.json()["data"]["args"] == ["proj_001"]
    assert cancel_response.json()["data"]["command"] == "cancel"
    assert cancel_response.json()["data"]["args"] == ["proj_001"]


def test_receive_feishu_interactive_acknowledges_action():
    client = make_client()

    response = client.post(
        "/api/feishu/interactive",
        json={
            "action": "escalation_decision",
            "user_id": "feishu_user_001",
            "project_id": "proj_001",
            "escalation_id": "esc_001",
            "value": {"decision": "continue", "comment": "再自动修复一轮"},
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["accepted"] is True
    assert data["source"] == "feishu"
    assert data["action"] == "escalation_decision"
    assert data["user_id"] == "feishu_user_001"
    assert data["project_id"] == "proj_001"
    assert data["escalation_id"] == "esc_001"
    assert data["value"]["decision"] == "continue"


def test_escalation_decision_interactive_updates_escalation():
    client = make_client()
    project_id = create_project(client)
    escalation_id = create_escalation(client, project_id)

    response = client.post(
        "/api/feishu/interactive",
        json={
            "action": "escalation_decision",
            "user_id": "feishu_user_001",
            "project_id": project_id,
            "escalation_id": escalation_id,
            "value": {"decision": "continue", "comment": "继续自动修复"},
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["handled"] is True
    assert data["escalation"]["id"] == escalation_id
    assert data["escalation"]["status"] == "decided"
    assert data["escalation"]["decision"] == "continue"
    assert data["escalation"]["decision_comment"] == "继续自动修复"
