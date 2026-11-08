from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import Detection, ExpertReview
from ..schemas import HotspotOut, HotspotsResponse, ReportPoint
from ..services import hotspots as hs
from ..services.catalogue import UNASSESSED

router = APIRouter(tags=["map"])
VERIFIED = ("confirmed", "corrected")


def _load(db: Session, days: int, min_confidence: float):
    """Disease reports with GPS inside the time window. Expert-verified answers replace the AI label."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    q = (select(Detection, ExpertReview)
         .outerjoin(ExpertReview, ExpertReview.detection_id == Detection.id)
         .where(Detection.created_at >= since, Detection.latitude.is_not(None), Detection.longitude.is_not(None)))
    reports = []
    for det, rev in db.execute(q).all():
        verified = bool(rev and rev.status in VERIFIED)
        disease = rev.expert_disease if verified and rev.expert_disease else det.disease
        crop = rev.expert_crop if verified and rev.expert_crop else det.crop
        if disease.strip().lower() == "healthy" or (not verified and disease == UNASSESSED):
            continue
        if not verified and det.confidence < min_confidence:
            continue                      # weak, unverified guesses would create false hotspots
        created = det.created_at if det.created_at.tzinfo else det.created_at.replace(tzinfo=timezone.utc)
        reports.append(hs.Report(str(det.id), disease, crop, det.latitude, det.longitude, created, verified))
    return reports


@router.get("/reports", response_model=list[ReportPoint])
def reports(days: int = Query(settings.hotspot_window_days, ge=1, le=90),
            min_confidence: float = Query(settings.hotspot_min_confidence, ge=0, le=100),
            disease: str | None = None, db: Session = Depends(get_db)):
    """Map points. Coordinates are rounded to ~1 km for the public view."""
    items = _load(db, days, min_confidence)
    if disease:
        items = [r for r in items if r.disease.lower() == disease.lower()]
    return [ReportPoint(disease=r.disease, crop=r.crop, latitude=round(r.lat, hs.PUBLIC_DECIMALS),
                        longitude=round(r.lon, hs.PUBLIC_DECIMALS), created_at=r.created_at, verified=r.verified)
            for r in items]


@router.get("/hotspots", response_model=HotspotsResponse)
def hotspots(min_reports: int = Query(settings.hotspot_min_reports, ge=2, le=100),
             radius_km: float = Query(settings.hotspot_radius_km, gt=0, le=100),
             days: int = Query(settings.hotspot_window_days, ge=1, le=90),
             min_confidence: float = Query(settings.hotspot_min_confidence, ge=0, le=100),
             db: Session = Depends(get_db)):
    found = hs.find_hotspots(_load(db, days, min_confidence), min_reports, radius_km)
    return HotspotsResponse(
        parameters={"min_reports": min_reports, "radius_km": radius_km, "window_days": days,
                    "min_confidence": min_confidence},
        note="Potential hotspots are prototype threshold matches on AI-suggested reports, not confirmed outbreaks.",
        hotspots=[HotspotOut(disease=h.disease, latitude=h.center_lat, longitude=h.center_lon, radius_km=h.radius_km,
                             report_count=h.report_count, verified_count=h.verified_count, confirmed=h.confirmed,
                             crops=h.crops, first_report=h.first_report, last_report=h.last_report)
                  for h in found])
