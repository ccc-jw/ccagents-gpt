import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class AppSettings:
    name: str = "Hermes Agent Software Team"


@dataclass
class DatabaseConfig:
    path: str = "data/app.db"


@dataclass
class ModelDefaults:
    provider: str = "openai-compatible"
    base_url: str = ""
    api_key_env: str = "DEFAULT_MODEL_API_KEY"
    api_key: str | None = None
    model: str = "claude-opus-4-7"
    temperature: float = 0.2
    max_tokens: int = 8192
    timeout_seconds: int = 300
    max_retries: int = 2


@dataclass
class ModelConfig:
    defaults: ModelDefaults = field(default_factory=ModelDefaults)
    agents: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class ResolvedModelConfig:
    provider: str
    base_url: str
    api_key_env: str
    api_key: str | None
    model: str
    temperature: float
    max_tokens: int
    timeout_seconds: int
    max_retries: int

    def public_dump(self) -> dict[str, Any]:
        data = asdict(self)
        if data.get("api_key"):
            data["api_key"] = "***"
        return data


@dataclass
class AppConfig:
    app: AppSettings = field(default_factory=AppSettings)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    model: ModelConfig = field(default_factory=ModelConfig)

    def public_dump(self) -> dict[str, Any]:
        data = asdict(self)
        defaults = data["model"]["defaults"]
        if defaults.get("api_key"):
            defaults["api_key"] = "***"
        for agent_config in data["model"].get("agents", {}).values():
            if agent_config.get("api_key"):
                agent_config["api_key"] = "***"
        return data


def load_config(path: str | Path | None = None) -> AppConfig:
    config_path = Path(path) if path is not None else Path("configs/app.yaml")
    raw: dict[str, Any] = {}
    if config_path.exists():
        raw = yaml.safe_load(config_path.read_text()) or {}

    app = AppSettings(**raw.get("app", {}))
    database = DatabaseConfig(**raw.get("database", {}))
    model_raw = raw.get("model", {})
    model = ModelConfig(
        defaults=ModelDefaults(**model_raw.get("defaults", {})),
        agents=model_raw.get("agents", {}),
    )

    database_override = os.getenv("HERMES_DATABASE_PATH")
    if database_override:
        database.path = database_override

    return AppConfig(app=app, database=database, model=model)


def _agent_config_keys(agent_name: str) -> list[str]:
    normalized = agent_name.lower()
    aliases = {
        "pm": "project_manager",
        "pdm": "product_manager",
        "res": "researcher",
        "researcher": "researcher",
        "arch": "architect",
        "dev": "developer",
        "test": "tester",
        "sec": "security",
    }
    keys = [normalized]
    alias = aliases.get(normalized)
    if alias and alias not in keys:
        keys.append(alias)
    return keys


def resolve_model_config(config: AppConfig, agent_name: str) -> ResolvedModelConfig:
    values = asdict(config.model.defaults)
    for key in _agent_config_keys(agent_name):
        values.update(config.model.agents.get(key, {}))
    if not values.get("api_key") and values.get("api_key_env"):
        values["api_key"] = os.getenv(values["api_key_env"])
    return ResolvedModelConfig(**values)
