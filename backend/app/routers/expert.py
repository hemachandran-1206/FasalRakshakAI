import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user, require_role
from ..models import ExpertReview, User
from ..schemas import DecisionIn, ReviewDetail, ReviewSummary
from ..services import advisories, reviews

router = APIRouter(tags=["expert"])
expert_only = require_role("expert")


def _own_review(db: Session, review_id: uuid.UUID, expert: User) -> ExpertReview:
    review = db.get(ExpertReview, review_id)
    if not review or review.assigned_expert_id != expert.id:     # 404, not 403: don't reveal other cases exist
        raise HTTPException(404, "Review not found")
    return review


@router.get("/expert/reviews", response_model=list[ReviewSummary])
def my_reviews(status: str | None = Query("assigned", pattern="^(assigned|confirmed|corrected|inconclusive|all)$"),
               expert: User = Depends(expert_only), db: Session = Depends(get_db)):
    q = select(ExpertReview).where(ExpertReview.assigned_expert_id == expert.id)
    if status != "all":
        q = q.where(ExpertReview.status == status)
    items = db.scalars(q.order_by(ExpertReview.needs_attention.desc(), ExpertReview.created_at)).all()
    return [reviews.summary(r, {expert.id: expert}) for r in items]


@router.get("/expert/reviews/{review_id}", response_model=ReviewDetail)
def my_review(review_id: uuid.UUID, expert: User = Depends(expert_only), db: Session = Depends(get_db)):
    return reviews.detail(db, _own_review(db, review_id, expert), exact_location=False)


@router.post("/expert/reviews/{review_id}/decision", response_model=ReviewDetail)
def decision(review_id: uuid.UUID, data: DecisionIn, expert: User = Depends(expert_only), db: Session = Depends(get_db)):
    review = _own_review(db, review_id, expert)
    try:
        reviews.decide(review, expert, data)
    except reviews.WorkflowError as e:
        raise HTTPException(e.status, e.message)
    if data.decision != "inconclusive" and (data.advice_management or data.advice_prevention):
        if not (data.advice_management or "").strip() or not (data.advice_prevention or "").strip():
            db.rollback()
            raise HTTPException(422, "Give both management and prevention advice, or neither")
        advisories.suggest_from_expert(db, crop=review.expert_crop, disease=review.expert_disease,
                                       management=data.advice_management, prevention=data.advice_prevention,
                                       expert_name=expert.full_name)
    db.commit()
    return reviews.detail(db, review, exact_location=False)


@router.get("/reviews/{review_id}/image")
def review_image(review_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Farmers' photos are private: only admins and the assigned expert may view them."""
    review = db.get(ExpertReview, review_id)
    allowed = review and (user.role == "admin" or (user.role == "expert" and review.assigned_expert_id == user.id))
    if not allowed:
        raise HTTPException(404, "Image not found")
    path = Path(review.detection.image_path)
    if not path.is_file():
        raise HTTPException(404, "Image file is not available")
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=300"})
