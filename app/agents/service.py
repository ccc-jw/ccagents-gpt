import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.agents.schemas import AgentCreateRequest
from app.core.config import load_config, resolve_model_config
from app.core.database import get_connection


def _now():
    return datetime.now(timezone.utc).isoformat()


def _decode_agent(row):
    if row is None:
        return None
    data = dict(row)
    data["enabled"] = bool(data["enabled"])
    data["model_config"] = json.loads(data.pop("model_config_json") or "{}")
    return data


def create_agent(database_path: str, request: AgentCreateRequest):
    agent_id = f"agent_{uuid4().hex}"
    now = _now()
    with get_connection(database_path) as connection:
        connection.execute(
            """
            INSERT INTO agents (id, name, role, description, enabled, model_config_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                agent_id,
                request.name,
                request.role,
                request.description,
                1 if request.enabled else 0,
                json.dumps(request.model_overrides, ensure_ascii=False),
                now,
                now,
            ),
        )
    return get_agent(database_path, agent_id)


def get_agent(database_path: str, agent_id: str):
    with get_connection(database_path) as connection:
        row = connection.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone()
    return _decode_agent(row)


def get_agent_by_name(database_path: str, name: str):
    with get_connection(database_path) as connection:
        row = connection.execute("SELECT * FROM agents WHERE name = ?", (name,)).fetchone()
    return _decode_agent(row)


def list_agents(database_path: str, enabled: bool | None):
    sql = "SELECT * FROM agents"
    params = []
    if enabled is not None:
        sql += " WHERE enabled = ?"
        params.append(1 if enabled else 0)
    with get_connection(database_path) as connection:
        rows = connection.execute(sql, params).fetchall()
    return [_decode_agent(row) for row in rows]


def set_agent_enabled(database_path: str, agent_id: str, enabled: bool):
    now = _now()
    with get_connection(database_path) as connection:
        connection.execute(
            "UPDATE agents SET enabled = ?, updated_at = ? WHERE id = ?",
            (1 if enabled else 0, now, agent_id),
        )
    return get_agent(database_path, agent_id)


def resolve_agent_model_config(config_path: str | Path | None, agent_name: str):
    return resolve_model_config(load_config(config_path), agent_name).public_dump()
