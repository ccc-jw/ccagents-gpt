from fastapi import APIRouter, HTTPException, Request

from app.core.responses import success_response
from app.reviews import service
from app.reviews.schemas import ReviewCommentRequest, ReviewCompleteRequest, ReviewCreateRequest

router = APIRouter()


def _database_path(request: Request) -> str:
    return request.app.state.database_path


@router.post("/api/projects/{project_id}/reviews")
def create_review(project_id: str, request_body: ReviewCreateRequest, request: Request):
    return success_response(service.create_review(_database_path(request), project_id, request_body))


@router.get("/api/projects/{project_id}/reviews")
def list_reviews(project_id: str, request: Request):
    return success_response(service.list_reviews(_database_path(request), project_id))


@router.get("/api/reviews/{review_id}")
def get_review(review_id: str, request: Request):
    return success_response(service.get_review(_database_path(request), review_id))


@router.post("/api/reviews/{review_id}/comments")
def add_review_comment(review_id: str, request_body: ReviewCommentRequest, request: Request):
    return success_response(service.add_review_comment(_database_path(request), review_id, request_body))


@router.post("/api/reviews/{review_id}/complete")
def complete_review(review_id: str, request_body: ReviewCompleteRequest, request: Request):
    return success_response(service.complete_review(_database_path(request), review_id, request_body))


@router.post("/api/reviews/{review_id}/evaluate-gate")
def evaluate_review_gate(review_id: str, request: Request):
    try:
        return success_response(service.evaluate_review_gate(_database_path(request), review_id))
    except service.ReviewGateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
