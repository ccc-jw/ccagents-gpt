import yaml

from app.core.config import load_config


def test_load_config_reads_yaml_and_environment_override(tmp_path, monkeypatch):
    config_path = tmp_path / "app.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "app": {"name": "Hermes Test"},
                "database": {"path": "data/app.db"},
                "model": {
                    "defaults": {
                        "provider": "openai-compatible",
                        "base_url": "https://api.example.com/v1",
                        "api_key_env": "DEFAULT_MODEL_API_KEY",
                        "api_key": "secret-value",
                        "model": "claude-opus-4-7",
                        "temperature": 0.2,
                        "max_tokens": 8192,
                        "timeout_seconds": 300,
                        "max_retries": 2,
                    }
                },
            }
        )
    )
    monkeypatch.setenv("HERMES_DATABASE_PATH", "override/app.db")

    config = load_config(config_path)

    assert config.app.name == "Hermes Test"
    assert config.database.path == "override/app.db"
    assert config.model.defaults.base_url == "https://api.example.com/v1"
    assert config.model.defaults.api_key_env == "DEFAULT_MODEL_API_KEY"


def test_public_dump_redacts_plain_api_key(tmp_path):
    config_path = tmp_path / "app.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "app": {"name": "Hermes Test"},
                "database": {"path": "data/app.db"},
                "model": {
                    "defaults": {
                        "provider": "openai-compatible",
                        "base_url": "https://api.example.com/v1",
                        "api_key_env": "DEFAULT_MODEL_API_KEY",
                        "api_key": "secret-value",
                        "model": "claude-opus-4-7",
                    }
                },
            }
        )
    )

    public_dump = load_config(config_path).public_dump()

    assert "secret-value" not in str(public_dump)
    assert public_dump["model"]["defaults"]["api_key"] == "***"
