"""Triage: what the farmer is told. Four outcomes, from most to least certain:
   healthy   - looks healthy (needs high confidence)
   diagnosed - confident AND we have stored advice for it
   likely    - plausible but not certain: show the top candidates, an expert still reviews
   escalated - the AI should not guess (unsupported crop, low confidence, no advice): an expert decides
Everything is preliminary until an expert verifies the case. Without a farmer-selected crop, or with a poor photo,
the answer is capped at 'likely', because unrestricted predictions are much less reliable (see your notebook, stage 4)."""
from ..config import settings
from . import treatments
from . import i18n
from .catalogue import UNASSESSED

INTERIM_ADVICE = ("Until an expert confirms: separate the affected plants if you can, avoid watering the leaves from above, "
                  "and do not spray anything before checking with your local Krishi Vigyan Kendra (KVK).")
ESCALATION_MESSAGES = {
    "unsupported_crop": "Our AI cannot assess {crop} yet, so your photo has been sent to an agricultural expert.",
    "low_confidence": "The AI is not sure about this photo, so it has been sent to an agricultural expert. "
                      "A close-up photo of one leaf in good daylight can help.",
    "no_advice": "The AI found a possible problem but we have no verified advice for it yet, so an expert will review it.",
}


def triage(plant: str, disease: str, confidence: float, *, crop_selected: bool, quality_ok: bool) -> tuple[str, str | None]:
    """-> (status, reason). `reason` explains escalations and caps."""
    if confidence < settings.likely_threshold:
        return "escalated", "low_confidence"
    confident = confidence >= settings.confidence_threshold
    if treatments.is_healthy_label(disease):
        return ("healthy", None) if confident and crop_selected and quality_ok else ("likely", _cap_reason(crop_selected, quality_ok, confident))
    if confident and treatments.get_treatment(plant, disease) is None:
        return "escalated", "no_advice"
    if confident and crop_selected and quality_ok:
        return "diagnosed", None
    return "likely", _cap_reason(crop_selected, quality_ok, confident)


def _cap_reason(crop_selected: bool, quality_ok: bool, confident: bool) -> str:
    if not crop_selected:
        return "crop_not_selected"
    if not quality_ok:
        return "poor_photo"
    return "medium_confidence"


HINTS = {"crop_not_selected": "Choose your crop before uploading for a more reliable result.",
         "poor_photo": "A sharper photo would give a more reliable result.",
         "medium_confidence": None}


def render(status: str, reason: str | None, *, crop: str, disease: str, confidence: float, candidates: list | None,
           lang: str = "en") -> dict:
    """The dict the farmer sees. Built from stored values so the lookup page matches the upload page."""
    if status == "healthy":
        return {"status": status, "message": i18n.t("healthy", lang, crop=crop.lower()),
                "confidence": confidence}
    if status == "diagnosed":
        info = treatments.get_treatment(crop, disease)
        if info:
            return {"status": status, "plant": crop, "disease": disease, "confidence": confidence,
                    "recommendation": info["recommendation"], "cultural_practice": info["cultural_practice"]}
        status, reason = "escalated", "no_advice"
    if status == "likely":
        top = (candidates or [])[:2] or [{"plant": crop, "disease": disease, "confidence": confidence}]
        return {"status": status, "reason": reason, "candidates": top, "hint": i18n.t(f"hint_{reason}", lang) if HINTS.get(reason) else None,
                "message": i18n.t("likely", lang), "interim_advice": i18n.t("interim", lang)}
    msg = i18n.t(f"esc_{reason if reason in ESCALATION_MESSAGES else 'low_confidence'}", lang, crop=crop)
    return {"status": "escalated", "reason": reason, "message": msg, "unassessed": disease == UNASSESSED}
