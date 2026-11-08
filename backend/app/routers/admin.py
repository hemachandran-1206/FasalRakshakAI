import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_role
from ..models import ExpertReview, User
from ..schemas import AssignIn, ExpertCreateIn, ExpertOut, ReviewDetail, ReviewSummary
from ..services import reviews, security

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_role("admin"))])
admin_only = require_role("admin")


@router.post("/experts", response_model=ExpertOut, status_code=201)
def create_expert(data: ExpertCreateIn, db: Session = Depends(get_db)):
    email = data.email.strip().lower()
    if "@" not in email or len(email) > 255:
        raise HTTPException(422, "Enter a valid email address")
    if len(data.password) < security.MIN_PASSWORD_LENGTH:
        raise HTTPException(422, f"Password must be at least {security.MIN_PASSWORD_LENGTH} characters")
    if not data.full_name.strip():
        raise HTTPException(422, "Name is required")
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists")
    user = User(email=email, full_name=data.full_name.strip(), role="expert",
                password_hash=security.hash_password(data.password))
    db.add(user)
    db.commit()
    return ExpertOut.model_validate(user)


@router.get("/experts", response_model=list[ExpertOut])
def list_experts(db: Session = Depends(get_db)):
    open_counts = dict(db.execute(
        select(ExpertReview.assigned_expert_id, func.count()).where(ExpertReview.status == "assigned")
        .group_by(ExpertReview.assigned_expert_id)).all())
    experts = db.scalars(select(User).where(User.role == "expert").order_by(User.full_name)).all()
    return [ExpertOut(**{**e.__dict__, "open_cases": open_counts.get(e.id, 0)}) for e in experts]


@router.get("/reviews", response_model=list[ReviewSummary])
def review_queue(status: str | None = Query(None, pattern="^(pending|assigned|confirmed|corrected|inconclusive)$"),
                 needs_attention: bool | None = None, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                 db: Session = Depends(get_db)):
    q = select(ExpertReview)
    if status:
        q = q.where(ExpertReview.status == status)
    if needs_attention is not None:
        q = q.where(ExpertReview.needs_attention == needs_attention)
    q = q.order_by(ExpertReview.needs_attention.desc(), ExpertReview.created_at).limit(limit).offset(offset)
    items = db.scalars(q).all()
    ids = {r.assigned_expert_id for r in items} - {None}
    people = {u.id: u for u in db.scalars(select(User).where(User.id.in_(ids)))} if ids else {}
    return [reviews.summary(r, people) for r in items]


@router.get("/reviews/{review_id}", response_model=ReviewDetail)
def review_detail(review_id: uuid.UUID, db: Session = Depends(get_db)):
    review = db.get(ExpertReview, review_id)
    if not review:
        raise HTTPException(404, "Review not found")
    return reviews.detail(db, review, exact_location=True)


@router.post("/reviews/{review_id}/assign", response_model=ReviewDetail)
def assign(review_id: uuid.UUID, data: AssignIn, admin=Depends(admin_only), db: Session = Depends(get_db)):
    review, expert = db.get(ExpertReview, review_id), db.get(User, data.expert_id)
    if not review or not expert:
        raise HTTPException(404, "Review or expert not found")
    try:
        reviews.assign(review, expert, admin)
    except reviews.WorkflowError as e:
        raise HTTPException(e.status, e.message)
    db.commit()
    return reviews.detail(db, review, exact_location=True)
