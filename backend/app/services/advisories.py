"""Multilingual advisories (roadmap Phase 4).

Rows live in the `advisories` table, one per (crop, disease, language), pre-translated and reviewed by a person.
Serving rule, safest first:
  1. a *verified* advisory in the farmer's language;
  2. otherwise a *verified* English advisory, then the built-in English knowledge base (treatments.py),
     with `translation_pending=True` so the UI can say the advice is shown in English;
  3. nothing -> None (the caller escalates to an expert).
Drafts (machine translations, expert-written text) are NEVER shown to farmers until a staff member verifies them.
Editing a verified row sends it back to draft, so a changed text can't ride on an old approval."""
import csv
import io
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Advisory, User
from . import i18n, treatments

CSV_FIELDS = ["crop", "disease", "language", "symptoms", "prevention", "management", "source", "source_url"]


def _find(db: Session, crop: str, disease: str, lang: str) -> Advisory | None:
    return db.scalar(select(Advisory).where(func.lower(Advisory.crop) == crop.strip().lower(),
                                            func.lower(Advisory.disease) == disease.strip().lower(),
                                            Advisory.language == lang))


def resolve(db: Session, crop: str, disease: str, lang: str | None) -> dict | None:
    """-> {recommendation, cultural_practice, symptoms, language, translation_pending, source} or None."""
    lang = i18n.norm_lang(lang)
    for want in ([lang, "en"] if lang != "en" else ["en"]):
        adv = _find(db, crop, disease, want)
        if adv and adv.verification_status == "verified":
            return {"recommendation": adv.management, "cultural_practice": adv.prevention, "symptoms": adv.symptoms,
                    "language": want, "translation_pending": want != lang, "source": adv.source}
    info = treatments.get_treatment(crop, disease)
    if info:
        return {"recommendation": info["recommendation"], "cultural_practice": info["cultural_practice"], "symptoms": "",
                "language": "en", "translation_pending": lang != "en", "source": "FasalRakshak built-in knowledge base"}
    return None


def localize_care(db: Session, care: dict | None, lang: str | None) -> dict | None:
    """Swap the English treatment text in a rendered 'diagnosed' care dict for the farmer's language."""
    if not care or care.get("status") != "diagnosed":
        return care
    adv = resolve(db, care["plant"], care["disease"], lang)
    if adv:
        care = {**care, "recommendation": adv["recommendation"], "cultural_practice": adv["cultural_practice"],
                "language": adv["language"], "translation_pending": adv["translation_pending"]}
        if adv["translation_pending"]:
            care["translation_note"] = i18n.t("translation_pending", lang)
    return care


def upsert(db: Session, *, crop: str, disease: str, language: str, symptoms: str = "", prevention: str = "",
           management: str = "", source: str = "", source_url: str = "") -> Advisory:
    """Create or edit an advisory; the result is always a draft until verify() is called."""
    if language not in i18n.LANGS:
        raise ValueError(f"language must be one of {i18n.LANGS}")
    crop, disease = crop.strip(), disease.strip()
    if not crop or not disease:
        raise ValueError("crop and disease are required")
    adv = _find(db, crop, disease, language)
    if adv is None:
        adv = Advisory(crop=crop, disease=disease, language=language)
        db.add(adv)
    adv.symptoms, adv.prevention, adv.management = symptoms.strip(), prevention.strip(), management.strip()
    adv.source, adv.source_url = source.strip(), source_url.strip()
    adv.verification_status, adv.verified_by = "draft", None
    db.flush()
    return adv


def suggest_from_expert(db: Session, *, crop: str, disease: str, management: str, prevention: str, expert_name: str) -> Advisory | None:
    """An expert's own advice becomes an English draft. Never overwrites an existing row (it may be verified)."""
    if _find(db, crop, disease, "en"):
        return None
    return upsert(db, crop=crop, disease=disease, language="en", management=management, prevention=prevention,
                  source=f"Expert: {expert_name} (case review)")


def verify(db: Session, adv: Advisory, user: User) -> Advisory:
    if not adv.management.strip() or not adv.prevention.strip():
        raise ValueError("management and prevention must both be filled in before verifying")
    adv.verification_status, adv.verified_by = "verified", user.id
    db.flush()
    return adv


def export_csv(db: Session, *, with_template: bool = True) -> str:
    """One row per (built-in disease x language) so a translator can fill the blanks; existing rows are included as-is."""
    rows: dict[tuple, dict] = {}
    if with_template:
        for entry in treatments._BUILTIN.values():
            for lang in i18n.LANGS:
                rows[(entry["plant"].lower(), entry["disease"].lower(), lang)] = {
                    "crop": entry["plant"], "disease": entry["disease"], "language": lang, "symptoms": "",
                    "prevention": entry["cultural_practice"] if lang == "en" else "",
                    "management": entry["recommendation"] if lang == "en" else "", "source": "", "source_url": ""}
    for a in db.scalars(select(Advisory)):
        rows[(a.crop.lower(), a.disease.lower(), a.language)] = {
            "crop": a.crop, "disease": a.disease, "language": a.language, "symptoms": a.symptoms,
            "prevention": a.prevention, "management": a.management, "source": a.source, "source_url": a.source_url}
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=CSV_FIELDS)
    w.writeheader()
    for key in sorted(rows):
        w.writerow(rows[key])
    return out.getvalue()


def import_csv(db: Session, text: str) -> dict:
    """Upsert rows as DRAFTS. Rows with no management/prevention text (blank template rows) are skipped."""
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    missing = set(CSV_FIELDS[:3] + ["prevention", "management"]) - set(reader.fieldnames or [])
    if missing:
        raise ValueError(f"CSV is missing columns: {', '.join(sorted(missing))}")
    done = skipped = 0
    errors: list[str] = []
    for n, row in enumerate(reader, start=2):
        if not (row.get("management") or "").strip() and not (row.get("prevention") or "").strip():
            skipped += 1
            continue
        try:
            upsert(db, crop=row["crop"], disease=row["disease"], language=(row["language"] or "").strip().lower(),
                   symptoms=row.get("symptoms") or "", prevention=row.get("prevention") or "",
                   management=row.get("management") or "", source=row.get("source") or "",
                   source_url=row.get("source_url") or "")
            done += 1
        except ValueError as e:
            errors.append(f"line {n}: {e}")
    return {"imported_as_draft": done, "skipped_blank": skipped, "errors": errors}


def get(db: Session, advisory_id: uuid.UUID) -> Advisory | None:
    return db.get(Advisory, advisory_id)
