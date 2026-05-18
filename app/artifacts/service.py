import json
from datetime import datetime, timezone
from uuid import uuid4

from app.artifacts.schemas import ArtifactCreateRequest, ArtifactVersionCreateRequest
from app.core.database import get_connection


def _now():
    return datetime.now(timezone.utc).isoformat()


def _decode_artifact(row):
    if row is None:
        return None
    data = dict(row)
    data["metadata"] = json.loads(data.pop("metadata_json") or "{}")
    return data


def _decode_artifact_version(row):
    if row is None:
        return None
    data = dict(row)
    data["metadata"] = json.loads(data.pop("metadata_json") or "{}")
    return data


def create_artifact(database_path: str, project_id: str, request: ArtifactCreateRequest):
    artifact_id = f"artifact_{uuid4().hex}"
    now = _now()
    with get_connection(database_path) as connection:
        connection.execute(
            """
            INSERT INTO artifacts (
                id, project_id, task_id, artifact_type, name, path, version,
                status, created_by, metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?)
            """,
            (
                artifact_id,
                project_id,
                request.task_id,
                request.artifact_type,
                request.name,
                request.path,
                request.version,
                request.created_by,
                json.dumps(request.metadata, ensure_ascii=False),
                now,
                now,
            ),
        )
        connection.execute(
            """
            INSERT INTO artifact_versions (
                id, artifact_id, version, path, created_by, change_summary, metadata_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"artifact_version_{uuid4().hex}",
                artifact_id,
                request.version,
                request.path,
                request.created_by,
                "初始版本",
                json.dumps(request.metadata, ensure_ascii=False),
                now,
            ),
        )
    return get_artifact(database_path, artifact_id)


def get_artifact(database_path: str, artifact_id: str):
    with get_connection(database_path) as connection:
        row = connection.execute("SELECT * FROM artifacts WHERE id = ?", (artifact_id,)).fetchone()
    return _decode_artifact(row)


def list_artifacts(
    database_path: str,
    project_id: str,
    artifact_type: str | None,
    created_by: str | None,
    status: str | None,
):
    sql = "SELECT * FROM artifacts WHERE project_id = ?"
    params = [project_id]
    if artifact_type:
        sql += " AND artifact_type = ?"
        params.append(artifact_type)
    if created_by:
        sql += " AND created_by = ?"
        params.append(created_by)
    if status:
        sql += " AND status = ?"
        params.append(status)
    with get_connection(database_path) as connection:
        rows = connection.execute(sql, params).fetchall()
    return [_decode_artifact(row) for row in rows]


def create_artifact_version(database_path: str, artifact_id: str, request: ArtifactVersionCreateRequest):
    version_id = f"artifact_version_{uuid4().hex}"
    now = _now()
    with get_connection(database_path) as connection:
        connection.execute(
            """
            INSERT INTO artifact_versions (
                id, artifact_id, version, path, created_by, change_summary, metadata_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                version_id,
                artifact_id,
                request.version,
                request.path,
                request.created_by,
                request.change_summary,
                json.dumps(request.metadata, ensure_ascii=False),
                now,
            ),
        )
        connection.execute(
            """
            UPDATE artifacts
            SET version = ?, path = ?, created_by = ?, metadata_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                request.version,
                request.path,
                request.created_by,
                json.dumps(request.metadata, ensure_ascii=False),
                now,
                artifact_id,
            ),
        )
        row = connection.execute("SELECT * FROM artifact_versions WHERE id = ?", (version_id,)).fetchone()
    return _decode_artifact_version(row)


def list_artifact_versions(database_path: str, artifact_id: str):
    with get_connection(database_path) as connection:
        rows = connection.execute(
            "SELECT * FROM artifact_versions WHERE artifact_id = ? ORDER BY created_at ASC",
            (artifact_id,),
        ).fetchall()
    return [_decode_artifact_version(row) for row in rows]
