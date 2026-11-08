from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import Detection
from ..schemas import CaseStatusOut
from ..services import cases, security

router = APIRouter(tags=["cases"])


def _client_key(request: Request) -> str:
    if settings.trust_proxy_headers and request.headers.get("x-forwarded-for"):
        return request.headers["x-forwarded-for"].split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.get("/cases/{code}", response_model=CaseStatusOut)
def case_status(code: str, request: Request, lang: str = "en", db: Session = Depends(get_db)):
    """Public: a farmer enters the case code they were given to see the AI result and, once done, the expert's verdict."""
    if not security.lookup_limiter.hit(_client_key(request)):
        raise HTTPException(429, "Too many lookups. Please wait a few minutes and try again.")
    raw = cases.normalise(code)
    det = db.scalar(select(Detection).where(Detection.case_code == raw)) if len(raw) == cases.CODE_LEN else None
    if det is None:
        raise HTTPException(404, "No case found for that code. Check the code and try again.")
    return cases.status_for(det, db, lang)
