import json
from datetime import datetime, timezone
from uuid import uuid4

from app.core.database import get_connection
from app.projects import service as project_service
from app.workflows import service as workflow_service
from app.workflows.state_machine import can_transition
from app.reviews.schemas import ReviewCommentRequest, ReviewCompleteRequest, ReviewCreateRequest


GATE_TARGETS = {
    ("requirement_review", "passed"): "REQUIREMENT_APPROVED",
    ("requirement_review", "failed"): "REQUIREMENT_REVISION",
    ("design_review", "passed"): "DEVELOPMENT",
    ("design_review", "failed"): "DESIGN_TESTCASE_REVISION",
    ("testcase_review", "passed"): "DEVELOPMENT",
    ("testcase_review", "failed"): "DESIGN_TESTCASE_REVISION",
    ("acceptance_review", "passed"): "DONE",
    ("acceptance_review", "failed"): "DEVELOPMENT",
}


class ReviewGateError(ValueError):
    pass


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


def _gate_target_phase(review):
    try:
        return GATE_TARGETS[(review["type"], review["conclusion"])]
    except KeyError as exc:
        raise ReviewGateError("评审类型或结论不支持自动门禁") from exc


def evaluate_review_gate(database_path: str, review_id: str):
    review = get_review(database_path, review_id)
    if review is None:
        raise ReviewGateError("评审不存在")
    if review["status"] not in {"passed", "failed"} or review["conclusion"] not in {"passed", "failed"}:
        raise ReviewGateError("评审尚未完成或结论不支持自动门禁")
    project = project_service.get_project(database_path, review["project_id"])
    if project is None:
        raise ReviewGateError("项目不存在")
    if project["current_phase"] != review["phase"]:
        raise ReviewGateError("评审阶段与当前项目阶段不一致")
    to_phase = _gate_target_phase(review)
    if not can_transition(review["phase"], to_phase):
        raise ReviewGateError("目标阶段不允许从当前阶段进入")
    event_type = "review_gate_passed" if review["conclusion"] == "passed" else "review_gate_failed"
    project_service.update_project_phase(
        database_path,
        review["project_id"],
        review["phase"],
        to_phase,
        event_type,
        review["conclusion"],
        [review_id],
    )
    return {
        "review_id": review_id,
        "project_id": review["project_id"],
        "from_phase": review["phase"],
        "to_phase": to_phase,
        "conclusion": review["conclusion"],
        "workflow": workflow_service.get_workflow(database_path, review["project_id"]),
    }
