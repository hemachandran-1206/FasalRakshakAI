"""Phase 4: multilingual advisories. `public` serves farmers; `staff` lets admins/experts edit, verify, import and export."""
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_role
from ..models import Advisory, User
from ..schemas import AdvisoryIn, AdvisoryOut, ResolvedAdvisory
from ..services import advisories, i18n

public = APIRouter(tags=["advisories"])
staff = APIRouter(prefix="/admin/advisories", tags=["advisories (staff)"])
any_staff = require_role("admin", "expert")
admin_only = require_role("admin")


@public.get("/languages")
def languages():
    return [{"code": c, "name": i18n.LANG_NAMES[c]} for c in i18n.LANGS]


@public.get("/advisories/{crop}/{disease}", response_model=ResolvedAdvisory)
def get_advisory(crop: str, disease: str, lang: str = "en", db: Session = Depends(get_db)):
    """What a farmer would see: verified text in `lang`, else English with translation_pending=true."""
    found = advisories.resolve(db, crop, disease, lang)
    if found is None:
        raise HTTPException(404, "No advice stored for this disease yet")
    return found


@staff.get("", response_model=list[AdvisoryOut])
def list_advisories(language: str | None = None, status: str | None = Query(None, pattern="^(draft|verified)$"),
                    crop: str | None = None, user: User = Depends(any_staff), db: Session = Depends(get_db)):
    q = select(Advisory).order_by(Advisory.crop, Advisory.disease, Advisory.language)
    if language:
        q = q.where(Advisory.language == language)
    if status:
        q = q.where(Advisory.verification_status == status)
    if crop:
        q = q.where(Advisory.crop.ilike(crop))
    return db.scalars(q).all()


@staff.put("", response_model=AdvisoryOut)
def save_advisory(data: AdvisoryIn, user: User = Depends(any_staff), db: Session = Depends(get_db)):
    """Create or edit. The row always comes back as a draft; verify it separately."""
    try:
        adv = advisories.upsert(db, **data.model_dump())
    except ValueError as e:
        raise HTTPException(422, str(e))
    db.commit()
    return adv


@staff.post("/{advisory_id}/verify", response_model=AdvisoryOut)
def verify_advisory(advisory_id: uuid.UUID, user: User = Depends(any_staff), db: Session = Depends(get_db)):
    adv = advisories.get(db, advisory_id)
    if adv is None:
        raise HTTPException(404, "Advisory not found")
    try:
        advisories.verify(db, adv, user)
    except ValueError as e:
        raise HTTPException(422, str(e))
    db.commit()
    return adv


@staff.get("/export.csv", response_class=PlainTextResponse)
def export_csv(user: User = Depends(admin_only), db: Session = Depends(get_db)):
    return PlainTextResponse(advisories.export_csv(db), media_type="text/csv",
                             headers={"Content-Disposition": 'attachment; filename="advisories.csv"'})


@staff.post("/import")
async def import_csv(file: UploadFile = File(...), user: User = Depends(admin_only), db: Session = Depends(get_db)):
    """Rows are imported as drafts; a person must verify each before farmers see it."""
    try:
        result = advisories.import_csv(db, (await file.read()).decode("utf-8", errors="replace"))
    except ValueError as e:
        raise HTTPException(422, str(e))
    db.commit()
    return result
