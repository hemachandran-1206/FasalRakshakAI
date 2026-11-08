"""Farmer-facing case lookup by case code (no farmer accounts).
The code is the farmer's only 'key', so it is random (31^8 ~ 8.5e11), typeable (no 0/O/1/I/L) and lookups are rate-limited.
The public view never includes the photo, GPS, or the expert's name."""
import re
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Detection
from ..schemas import CaseAI, CaseExpert, CaseStatusOut, PestDetection, WeatherAssessmentOut, WeatherRiskOut
from . import advisories, care, i18n, treatments

ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"     # 31 symbols, no look-alikes
CODE_LEN = 8
_CLEAN = re.compile(r"[^A-Z0-9]")


def format_code(raw: str) -> str:
    return f"{raw[:4]}-{raw[4:]}"


def normalise(user_input: str) -> str:
    """'k7m2 qx9p', 'K7M2-QX9P' -> 'K7M2QX9P'"""
    return _CLEAN.sub("", user_input.upper())


def unique_code(db: Session) -> str:
    for _ in range(10):
        raw = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LEN))
        if not db.scalar(select(Detection.id).where(Detection.case_code == raw)):
            return raw
    raise RuntimeError("could not generate a unique case code")


MESSAGES = {
    "awaiting_review": "Your photo is waiting for an agricultural expert. The AI result below is preliminary. Check back later with this code.",
    "under_review": "An agricultural expert is reviewing your case. The AI result below is preliminary.",
    "verified": "An agricultural expert has verified this case.",
    "inconclusive": "The expert could not decide from this photo. Please upload a clearer photo, or contact your local Krishi Vigyan Kendra (KVK).",
}


def _localized(db, care_dict, lang):
    return advisories.localize_care(db, care_dict, lang) if db is not None else care_dict


def status_for(det: Detection, db: Session | None = None, lang: str = "en") -> CaseStatusOut:
    lang = i18n.norm_lang(lang)
    review = det.review
    state = review.status if review else "pending"
    stage = {"pending": "awaiting_review", "assigned": "under_review", "confirmed": "verified",
             "corrected": "verified", "inconclusive": "inconclusive"}[state]

    ai = CaseAI(crop=det.crop, disease=det.disease, confidence=det.confidence,
                care=_localized(db, care.render(det.care_status, (det.triage or {}).get("reason"), crop=det.crop,
                                                 disease=det.disease, confidence=det.confidence, candidates=det.top_k,
                                                 lang=lang), lang),
                pests=[PestDetection(**p) for p in det.pests])
    expert = final = None
    note = None
    if review and state in ("confirmed", "corrected"):
        expert = CaseExpert(crop=review.expert_crop, disease=review.expert_disease, notes=review.expert_notes,
                            reviewed_at=review.reviewed_at, agrees_with_ai=state == "confirmed")
        if treatments.is_healthy_label(review.expert_disease):
            note = i18n.t("expert_healthy", lang)
        else:
            info = advisories.resolve(db, review.expert_crop, review.expert_disease, lang) if db is not None \
                else treatments.get_treatment(review.expert_crop, review.expert_disease)
            if info:
                final = {"crop": review.expert_crop, "disease": review.expert_disease,
                         "recommendation": info["recommendation"], "cultural_practice": info["cultural_practice"],
                         "language": info.get("language", "en"), "translation_pending": info.get("translation_pending", False)}
                if final["translation_pending"]:
                    final["translation_note"] = i18n.t("translation_pending", lang)
            else:
                note = i18n.t("no_stored_advice", lang)
    elif review and state == "inconclusive" and review.expert_notes:
        expert = CaseExpert(crop=None, disease=None, notes=review.expert_notes, reviewed_at=review.reviewed_at,
                            agrees_with_ai=False)

    weather = None
    if det.weather_risks:
        w = det.weather_risks[0]
        weather = WeatherAssessmentOut(
            temperature_c=w.temperature_c, humidity_pct=w.humidity_pct, rainfall_7d_mm=w.rainfall_mm,
            risks=[WeatherRiskOut(disease=x.disease, crops=x.raw.get("crops", []), risk_level=x.risk_level,
                                  rule_id=x.rule_id, explanation=x.explanation,
                                  source_url=x.raw.get("source_url", ""), metrics=x.raw.get("metrics", {}))
                   for x in det.weather_risks])
    return CaseStatusOut(case_code=format_code(det.case_code), submitted_at=det.created_at, stage=stage,
                         message=i18n.t("case_" + {"awaiting_review": "awaiting_review", "under_review": "under_review", "verified": "verified", "inconclusive": "inconclusive"}[stage], lang), ai=ai, expert=expert, final_treatment=final,
                         treatment_note=note, weather=weather)
