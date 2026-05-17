import json
from datetime import datetime, timezone
from uuid import uuid4

from app.core.database import get_connection
from app.reviews.schemas import ReviewCommentRequest, ReviewCompleteRequest, ReviewCreateRequest


def _now():
    return datetime.now(timezone.utc).isoformat()


def _decode_review(row):
    if row is None:
        return None
    data = dict(row)
    data["participants"] = json.loads(data.pop("participants_json"))
    data["input_artifacts"] = json.loads(data.pop("input_artifacts_json") or "[]")
    return data


def _decode_comment(row):
    return dict(row) if row else None


def create_review(database_path: str, project_id: str, request: ReviewCreateRequest):
    review_id = f"review_{uuid4().hex}"
    now = _now()
    with get_connection(database_path) as connection:
        connection.execute(
            """
            INSERT INTO reviews (
                id, project_id, type, phase, round, status, owner_agent, participants_json,
                input_artifacts_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, 1, 'open', ?, ?, ?, ?, ?)
            """,
            (
                review_id,
                project_id,
                request.type,
                request.phase,
                request.owner_agent,
                json.dumps(request.participants, ensure_ascii=False),
                json.dumps(request.input_artifacts, ensure_ascii=False),
                now,
                now,
            ),
        )
    return get_review(database_path, review_id)


def get_review(database_path: str, review_id: str):
    with get_connection(database_path) as connection:
        row = connection.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
    return _decode_review(row)


def list_reviews(database_path: str, project_id: str):
    with get_connection(database_path) as connection:
        rows = connection.execute("SELECT * FROM reviews WHERE project_id = ?", (project_id,)).fetchall()
    return [_decode_review(row) for row in rows]


def add_review_comment(database_path: str, review_id: str, request: ReviewCommentRequest):
    comment_id = f"comment_{uuid4().hex}"
    now = _now()
    with get_connection(database_path) as connection:
        connection.execute(
            """
            INSERT INTO review_comments (
                id, review_id, reviewer_agent, status, severity, comment,
                required_change, related_artifact, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                comment_id,
                review_id,
                request.reviewer_agent,
                request.status,
                request.severity,
                request.comment,
                request.required_change,
                request.related_artifact,
                now,
            ),
        )
        row = connection.execute("SELECT * FROM review_comments WHERE id = ?", (comment_id,)).fetchone()
    return _decode_comment(row)


def complete_review(database_path: str, review_id: str, request: ReviewCompleteRequest):
    now = _now()
    with get_connection(database_path) as connection:
        connection.execute(
            """
            UPDATE reviews SET status = ?, conclusion = ?, completed_at = ?, updated_at = ? WHERE id = ?
            """,
            (request.conclusion, request.conclusion, now, now, review_id),
        )
    return get_review(database_path, review_id)
