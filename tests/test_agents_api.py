import tempfile

import yaml
from fastapi.testclient import TestClient

from app.main import create_app


def make_client(config_path=None):
    database = tempfile.NamedTemporaryFile(delete=False)
    return TestClient(create_app(database.name, config_path=config_path))


def create_agent(client, **overrides):
    payload = {
        "name": "DEV",
        "role": "developer",
        "description": "负责编码实现、自测和修复",
        "enabled": True,
        "model_config": {"model": "claude-opus-4-7", "timeout_seconds": 1200},
    }
    payload.update(overrides)
    return client.post("/api/agents", json=payload)


def test_create_and_get_agent():
    client = make_client()

    created = create_agent(client)

    assert created.status_code == 200
    body = created.json()
    assert body["success"] is True
    assert body["data"]["id"].startswith("agent_")
    assert body["data"]["name"] == "DEV"
    assert body["data"]["role"] == "developer"
    assert body["data"]["enabled"] is True
    assert body["data"]["model_config"] == {"model": "claude-opus-4-7", "timeout_seconds": 1200}
    assert "model_config_json" not in body["data"]
    assert "request_id" in body

    detail = client.get(f"/api/agents/{body['data']['id']}")

    assert detail.status_code == 200
    assert detail.json()["data"] == body["data"]


def test_list_agents_filters_by_enabled():
    client = make_client()
    create_agent(client, name="DEV", role="developer", enabled=True)
    create_agent(client, name="SEC", role="security", enabled=False)

    enabled = client.get("/api/agents", params={"enabled": True})
    disabled = client.get("/api/agents", params={"enabled": False})

    assert enabled.status_code == 200
    assert [agent["name"] for agent in enabled.json()["data"]] == ["DEV"]
    assert disabled.status_code == 200
    assert [agent["name"] for agent in disabled.json()["data"]] == ["SEC"]


def test_set_agent_enabled_updates_agent():
    client = make_client()
    agent_id = create_agent(client, name="TEST", role="tester", enabled=True).json()["data"]["id"]

    updated = client.post(f"/api/agents/{agent_id}/enabled", json={"enabled": False})

    assert updated.status_code == 200
    assert updated.json()["data"]["enabled"] is False
    detail = client.get(f"/api/agents/{agent_id}")
    assert detail.json()["data"]["enabled"] is False


def test_get_agent_model_config_returns_redacted_resolved_config(tmp_path, monkeypatch):
    config_path = tmp_path / "app.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "model": {
                    "defaults": {
                        "provider": "openai-compatible",
                        "base_url": "https://api.example.com/v1",
                        "api_key_env": "DEFAULT_MODEL_API_KEY",
                        "model": "claude-opus-4-7",
                        "temperature": 0.2,
                        "max_tokens": 8192,
                        "timeout_seconds": 300,
                        "max_retries": 2,
                    },
                    "agents": {
                        "developer": {
                            "model": "claude-sonnet-4-6",
                            "timeout_seconds": 1200,
                        }
                    },
                }
            }
        )
    )
    monkeypatch.setenv("DEFAULT_MODEL_API_KEY", "runtime-secret")
    client = make_client(config_path=config_path)

    response = client.get("/api/agents/DEV/model-config")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["provider"] == "openai-compatible"
    assert data["base_url"] == "https://api.example.com/v1"
    assert data["model"] == "claude-sonnet-4-6"
    assert data["temperature"] == 0.2
    assert data["timeout_seconds"] == 1200
    assert data["api_key"] == "***"
    assert "runtime-secret" not in str(data)
