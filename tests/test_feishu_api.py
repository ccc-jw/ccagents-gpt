import os
import tempfile
from unittest.mock import patch

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


def test_continue_escalation_decision_resumes_paused_project():
    client = make_client()
    project_id = create_project(client)
    escalation_id = create_escalation(client, project_id)
    post_event(client, f"/pause {project_id}")

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
    status = client.get(f"/api/projects/{project_id}/status")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["handled"] is True
    assert data["project_status"]["status"] == "active"
    assert data["reply_text"] == "项目已根据升级决策继续。"
    assert status.json()["data"]["status"] == "active"


def test_cancel_escalation_decision_cancels_project():
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
            "value": {"decision": "cancel", "comment": "终止当前需求"},
        },
    )
    status = client.get(f"/api/projects/{project_id}/status")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["handled"] is True
    assert data["project_status"]["status"] == "cancelled"
    assert data["reply_text"] == "项目已根据升级决策取消。"
    assert status.json()["data"]["status"] == "cancelled"


def test_manual_escalation_decision_pauses_project():
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
            "value": {"decision": "manual", "comment": "转人工处理"},
        },
    )
    status = client.get(f"/api/projects/{project_id}/status")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["handled"] is True
    assert data["project_status"]["status"] == "paused"
    assert data["reply_text"] == "项目已根据升级决策暂停，等待人工处理。"
    assert status.json()["data"]["status"] == "paused"


def test_change_requirement_escalation_decision_moves_project_to_requirement_revision():
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
            "value": {"decision": "change_requirement", "comment": "需要调整需求范围"},
        },
    )
    status = client.get(f"/api/projects/{project_id}/status")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["handled"] is True
    assert data["project_status"]["current_phase"] == "REQUIREMENT_REVISION"
    assert data["reply_text"] == "项目已根据升级决策进入需求修订。"
    assert status.json()["data"]["current_phase"] == "REQUIREMENT_REVISION"


def test_build_project_status_notification_payload():
    client = make_client()
    project_id = create_project(client)

    response = client.get(f"/api/feishu/projects/{project_id}/status-notification")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data == {
        "project_id": project_id,
        "message_type": "interactive",
        "card": {
            "title": "项目状态更新：用户登录功能",
            "content": "项目当前处于 INIT 阶段。",
            "fields": [
                {"label": "阶段", "value": "INIT"},
                {"label": "状态", "value": "active"},
            ],
            "risks": [],
            "pending_user_actions": [],
        },
    }


def test_send_project_status_notification_requires_webhook_config():
    client = make_client()
    project_id = create_project(client)

    response = client.post(f"/api/feishu/projects/{project_id}/status-notification/send")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data == {
        "sent": False,
        "reason": "feishu_webhook_url_not_configured",
        "payload": {
            "project_id": project_id,
            "message_type": "interactive",
            "card": {
                "title": "项目状态更新：用户登录功能",
                "content": "项目当前处于 INIT 阶段。",
                "fields": [
                    {"label": "阶段", "value": "INIT"},
                    {"label": "状态", "value": "active"},
                ],
                "risks": [],
                "pending_user_actions": [],
            },
        },
    }


def test_build_escalation_notification_payload():
    client = make_client()
    project_id = create_project(client)
    escalation_id = create_escalation(client, project_id)

    response = client.get(f"/api/feishu/escalations/{escalation_id}/notification")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data == {
        "project_id": project_id,
        "escalation_id": escalation_id,
        "message_type": "interactive",
        "card": {
            "title": "需要用户决策：问题连续 3 次验证失败，需要用户决策。",
            "content": "阶段：TEST_AND_SECURITY_VALIDATION；来源：PM；重试：3/3",
            "actions": [
                {"label": "继续自动处理", "value": {"decision": "continue"}},
                {"label": "转人工处理", "value": {"decision": "manual"}},
                {"label": "取消项目", "value": {"decision": "cancel"}},
            ],
        },
    }


def test_send_project_status_notification_posts_webhook_without_exposing_url():
    client = make_client()
    project_id = create_project(client)

    with patch.dict(os.environ, {"FEISHU_WEBHOOK_URL": "https://open.feishu.cn/webhook/secret-token"}):
        with patch("app.feishu.service.httpx.post") as post:
            post.return_value.status_code = 200
            post.return_value.text = "ok"

            response = client.post(f"/api/feishu/projects/{project_id}/status-notification/send")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["sent"] is True
    assert data["status_code"] == 200
    assert "webhook_url" not in data
    assert "secret-token" not in str(data)
    post.assert_called_once_with(
        "https://open.feishu.cn/webhook/secret-token",
        json=data["payload"],
        timeout=10,
    )


def test_send_escalation_notification_requires_webhook_config():
    client = make_client()
    project_id = create_project(client)
    escalation_id = create_escalation(client, project_id)

    response = client.post(f"/api/feishu/escalations/{escalation_id}/notification/send")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data == {
        "sent": False,
        "reason": "feishu_webhook_url_not_configured",
        "payload": {
            "project_id": project_id,
            "escalation_id": escalation_id,
            "message_type": "interactive",
            "card": {
                "title": "需要用户决策：问题连续 3 次验证失败，需要用户决策。",
                "content": "阶段：TEST_AND_SECURITY_VALIDATION；来源：PM；重试：3/3",
                "actions": [
                    {"label": "继续自动处理", "value": {"decision": "continue"}},
                    {"label": "转人工处理", "value": {"decision": "manual"}},
                    {"label": "取消项目", "value": {"decision": "cancel"}},
                ],
            },
        },
    }


def test_escalation_project_decisions_record_project_events():
    client = make_client()
    project_id = create_project(client)

    decisions = [
        ("continue", "project_resumed", "飞书升级决策继续项目"),
        ("manual", "project_paused", "飞书升级决策转人工处理"),
        ("cancel", "project_cancelled", "飞书升级决策取消项目"),
    ]
    for decision, _, _ in decisions:
        escalation_id = create_escalation(client, project_id)
        client.post(
            "/api/feishu/interactive",
            json={
                "action": "escalation_decision",
                "user_id": "feishu_user_001",
                "project_id": project_id,
                "escalation_id": escalation_id,
                "value": {"decision": decision, "comment": decision},
            },
        )

    workflow_escalation_id = create_escalation(client, project_id)
    client.post(
        "/api/feishu/interactive",
        json={
            "action": "escalation_decision",
            "user_id": "feishu_user_001",
            "project_id": project_id,
            "escalation_id": workflow_escalation_id,
            "value": {"decision": "change_requirement", "comment": "需要调整需求范围"},
        },
    )

    response = client.get(f"/api/projects/{project_id}/events")

    assert response.status_code == 200
    events_by_type = {event["event_type"]: event for event in response.json()["data"]}
    for _, event_type, reason in decisions:
        assert events_by_type[event_type]["payload"] == {"reason": reason}
    assert events_by_type["project_requirement_change_requested"]["payload"]["from_phase"] == "INIT"
    assert events_by_type["project_requirement_change_requested"]["payload"]["to_phase"] == "REQUIREMENT_REVISION"
    assert events_by_type["project_requirement_change_requested"]["payload"]["reason"] == "飞书升级决策变更需求"
