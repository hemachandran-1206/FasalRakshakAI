"""Review workflow (roadmap 4.4):  pending -> assigned -> confirmed | corrected | inconclusive.
The AI prediction stays on `detections`; the expert's answer goes on `expert_reviews`."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..models import ExpertReview, ReviewHistory, User
from ..schemas import DecisionIn, HistoryItem, PersonRef, ReviewDetail, ReviewSummary
from . import catalogue, hotspots
from .cases import format_code

FINAL = ("confirmed", "corrected", "inconclusive")


class WorkflowError(Exception):
    def __init__(self, status: int, message: str):
        self.status, self.message = status, message


def _log(review: ExpertReview, actor: User, action: str, from_status: str, note: str | None = None):
    review.history.append(ReviewHistory(actor_id=actor.id, action=action, from_status=from_status,
                                        to_status=review.status, note=note))


def assign(review: ExpertReview, expert: User, admin: User) -> None:
    if review.status in FINAL:
        raise WorkflowError(409, "This review is already completed")
    if expert.role != "expert":
        raise WorkflowError(422, "Cases can only be assigned to expert accounts")
    previous, was = review.assigned_expert_id, review.status
    review.assigned_expert_id, review.status = expert.id, "assigned"
    _log(review, admin, "reassigned" if previous else "assigned", was, f"assigned to {expert.full_name}")


def decide(review: ExpertReview, expert: User, data: DecisionIn) -> None:
    if review.status != "assigned" or review.assigned_expert_id != expert.id:
        raise WorkflowError(409, "This case is not assigned to you or is already completed")
    det, notes = review.detection, (data.notes or "").strip() or None
    was = review.status
    if data.decision == "confirm":
        review.status, review.expert_crop, review.expert_disease = "confirmed", det.crop, det.disease
    elif data.decision == "correct":
        crop, disease = (data.crop or "").strip(), (data.disease or "").strip()
        if not crop or not disease:
            raise WorkflowError(422, "A correction needs both crop and disease")
        crop = catalogue.canonical_crop_name(crop)                    # "tomato " -> "Tomato"; keeps typos out of hotspots/advice lookups
        disease = catalogue.canonical_disease_name(crop, disease)
        if crop.lower() == det.crop.lower() and disease.lower() == det.disease.lower():
            raise WorkflowError(422, "That matches the AI prediction; use 'confirm' instead")
        review.status, review.expert_crop, review.expert_disease = "corrected", crop, disease
    else:
        if not notes:
            raise WorkflowError(422, "Please give a reason when marking a case inconclusive")
        review.status = "inconclusive"
    review.expert_notes, review.reviewed_at = notes, datetime.now(timezone.utc)
    _log(review, expert, review.status, was, notes)


def summary(review: ExpertReview, experts: dict) -> ReviewSummary:
    d, e = review.detection, experts.get(review.assigned_expert_id)
    return ReviewSummary(id=review.id, case_code=format_code(d.case_code) if d.case_code else None, status=review.status, needs_attention=review.needs_attention,
                         created_at=review.created_at, reviewed_at=review.reviewed_at, ai_crop=d.crop,
                         ai_disease=d.disease, ai_confidence=d.confidence,
                         assigned_expert=PersonRef(id=e.id, full_name=e.full_name) if e else None)


def detail(db: Session, review: ExpertReview, exact_location: bool) -> ReviewDetail:
    ids = {h.actor_id for h in review.history if h.actor_id} | ({review.assigned_expert_id} - {None})
    people = {u.id: u for u in db.query(User).filter(User.id.in_(ids))} if ids else {}
    d = review.detection
    lat, lon = d.latitude, d.longitude
    if not exact_location and lat is not None:
        lat, lon = round(lat, hotspots.PUBLIC_DECIMALS), round(lon, hotspots.PUBLIC_DECIMALS)
    base = summary(review, people).model_dump()
    return ReviewDetail(
        **base, top_k=d.top_k, pests=d.pests, latitude=lat, longitude=lon,
        expert_crop=review.expert_crop, expert_disease=review.expert_disease, expert_notes=review.expert_notes,
        history=[HistoryItem(action=h.action, from_status=h.from_status, to_status=h.to_status, note=h.note,
                             actor_name=people[h.actor_id].full_name if h.actor_id in people else "System",
                             created_at=h.created_at) for h in review.history])
