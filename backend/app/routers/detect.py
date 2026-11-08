import io
import logging
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import Detection, ExpertReview, ReviewHistory, WeatherRisk
from ..schemas import DetectionOut, WeatherAssessmentOut, WeatherRiskOut
from ..services import advisories, care as care_service, i18n, cases, catalogue, quality, weather as weather_service

log = logging.getLogger(__name__)
router = APIRouter(tags=["detection"])
ALLOWED_TYPES = {"image/jpeg", "image/png"}


def get_pipeline(request: Request):
    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline is None:
        raise HTTPException(503, "Models are not loaded")
    return pipeline


def _to_out(det: Detection, care: dict | None = None) -> DetectionOut:
    out = DetectionOut.model_validate(det)
    out.case_code = cases.format_code(det.case_code) if det.case_code else None
    if det.review:
        out.review_id, out.review_status = det.review.id, det.review.status
    out.care = care
    out.warnings = (det.triage or {}).get("warnings", [])
    if det.weather_risks:
        first = det.weather_risks[0]
        out.weather = WeatherAssessmentOut(
            temperature_c=first.temperature_c, humidity_pct=first.humidity_pct, rainfall_7d_mm=first.rainfall_mm,
            risks=[WeatherRiskOut(disease=w.disease, crops=w.raw.get("crops", []), risk_level=w.risk_level,
                                  rule_id=w.rule_id, explanation=w.explanation,
                                  source_url=w.raw.get("source_url", ""), metrics=w.raw.get("metrics", {}))
                   for w in det.weather_risks])
    return out


@router.post("/detect", response_model=DetectionOut, status_code=201)
async def detect(
    file: UploadFile = File(...),
    latitude: float | None = Form(None, ge=-90, le=90),
    longitude: float | None = Form(None, ge=-180, le=180),
    crop: str | None = Form(None),
    lang: str = Form("en"),
    db: Session = Depends(get_db),
    pipeline=Depends(get_pipeline),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, "Upload a JPEG or PNG image")
    if (latitude is None) != (longitude is None):
        raise HTTPException(422, "Send both latitude and longitude, or neither")

    data = await file.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"Image larger than {settings.max_upload_mb} MB")
    try:
        image = Image.open(io.BytesIO(data)).convert("RGB")
    except (UnidentifiedImageError, OSError):
        raise HTTPException(422, "File is not a valid image")

    # the farmer's own crop choice is the strongest signal we have; "not sure"/empty means the AI must guess the crop too
    crop_in = (crop or "").strip()
    selected = None
    if crop_in and crop_in.lower() not in ("unknown", "not_sure", "notsure"):
        selected = catalogue.get_crop(crop_in)
        if selected is None:
            raise HTTPException(422, "Unknown crop. Pick one from the list.")
    try:
        photo = quality.check(image)
    except quality.PhotoTooSmall as e:
        raise HTTPException(422, str(e))

    pests = pipeline.predict_pests(image)            # pest detection does not depend on the crop
    if selected and not selected["ai_supported"]:
        # the disease model has no (or only one) class for this crop: do not let it guess, send it to an expert
        diseases, plant, disease, conf = [], selected["name"], catalogue.UNASSESSED, 0.0
        status, reason = "escalated", "unsupported_crop"
    else:
        diseases = pipeline.predict_disease(image, crop=selected["model_crop"] if selected else None)
        plant, disease, conf = diseases[0]["plant"], diseases[0]["disease"], diseases[0]["confidence"]
        status, reason = care_service.triage(plant, disease, conf, crop_selected=selected is not None,
                                             quality_ok=not photo["warnings"])
    care = advisories.localize_care(db, care_service.render(status, reason, crop=plant, disease=disease, confidence=conf,
                                                            candidates=diseases, lang=lang), lang)

    det_id = uuid.uuid4()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    image_path = settings.upload_dir / f"{det_id}.jpg"
    image.save(image_path, "JPEG", quality=90)

    det = Detection(id=det_id, case_code=cases.unique_code(db), image_path=str(image_path), crop=plant, disease=disease,
                    confidence=conf, top_k=diseases, pests=pests, care_status=status,
                    triage={"reason": reason, "crop_selected": selected is not None, "selected_crop": selected["id"] if selected else None,
                            "warnings": photo["warnings"], "photo": {k: photo[k] for k in ("width", "height", "blur_score")}},
                    latitude=latitude, longitude=longitude)
    # roadmap 4.4: every AI prediction automatically gets a pending review record
    review = ExpertReview(detection_id=det_id, status="pending", needs_attention=status == "escalated")
    review.history.append(ReviewHistory(action="created", from_status=None, to_status="pending",
                                        note="auto-created from AI prediction"))
    det.review = review

    # roadmap 4.2: weather risk is evaluated independently of the image result; a weather failure never blocks detection
    if latitude is not None:
        try:
            assessment = await weather_service.assess(latitude, longitude)
            for r in assessment.risks:
                det.weather_risks.append(WeatherRisk(
                    temperature_c=assessment.temperature_c, humidity_pct=assessment.humidity_pct,
                    rainfall_mm=assessment.rainfall_7d_mm, disease=r.disease, risk_level=r.risk_level,
                    rule_id=r.rule_id, explanation=r.explanation,
                    raw={"crops": r.crops, "source_url": r.source_url, "metrics": r.metrics,
                         "data_source": "Open-Meteo (gridded model data)"}))
        except (weather_service.WeatherUnavailable, weather_service.InsufficientData) as e:
            log.warning("weather risk skipped: %s", e)
    db.add(det)
    db.commit()
    return _to_out(det, care)


@router.get("/detections/{detection_id}", response_model=DetectionOut)
def get_detection(detection_id: uuid.UUID, lang: str = "en", db: Session = Depends(get_db)):
    det = db.get(Detection, detection_id)
    if det is None:
        raise HTTPException(404, "Detection not found")
    care = advisories.localize_care(db, care_service.render(det.care_status, (det.triage or {}).get("reason"), crop=det.crop,
                                    disease=det.disease, confidence=det.confidence, candidates=det.top_k, lang=lang), lang)
    return _to_out(det, care)
