import uuid
from datetime import datetime, timezone
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict


def _as_utc(v: datetime) -> datetime:
    """SQLite returns naive datetimes; the app stores UTC, so label them as UTC (Postgres already returns aware ones)."""
    return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v


UTCDatetime = Annotated[datetime, AfterValidator(_as_utc)]


class DiseaseCandidate(BaseModel):
    plant: str
    disease: str
    confidence: float


class PestDetection(BaseModel):
    pest: str
    confidence: float
    bbox_xyxy: list[float]


class DetectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    case_code: str | None = None      # shown to the farmer; used on the 'Check my case' page
    crop: str
    disease: str
    confidence: float
    care_status: str
    top_k: list[DiseaseCandidate]
    pests: list[PestDetection]
    latitude: float | None
    longitude: float | None
    created_at: UTCDatetime
    review_id: uuid.UUID | None = None
    review_status: str | None = None
    care: dict | None = None      # recommendation / message for the farmer
    weather: "WeatherAssessmentOut | None" = None   # independent of the image result (roadmap 4.2)
    warnings: list[str] = []          # photo-quality warnings


class WeatherRiskOut(BaseModel):
    disease: str
    crops: list[str]
    risk_level: str
    rule_id: str
    explanation: str
    source_url: str
    metrics: dict


class WeatherAssessmentOut(BaseModel):
    temperature_c: float | None
    humidity_pct: float | None
    rainfall_7d_mm: float | None
    risks: list[WeatherRiskOut]


DetectionOut.model_rebuild()


class ReportPoint(BaseModel):
    disease: str
    crop: str
    latitude: float
    longitude: float
    created_at: UTCDatetime
    verified: bool


class HotspotOut(BaseModel):
    disease: str
    latitude: float
    longitude: float
    radius_km: float
    report_count: int
    verified_count: int
    confirmed: bool
    crops: list[str]
    first_report: UTCDatetime
    last_report: UTCDatetime


class HotspotsResponse(BaseModel):
    parameters: dict
    note: str
    hotspots: list[HotspotOut]


# ---------- Phase 3: auth + expert validation ----------
from typing import Literal  # noqa: E402


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    preferred_language: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str


class ExpertCreateIn(BaseModel):
    email: str
    full_name: str
    password: str


class ExpertOut(UserOut):
    open_cases: int = 0


class AssignIn(BaseModel):
    expert_id: uuid.UUID


class DecisionIn(BaseModel):
    decision: Literal["confirm", "correct", "inconclusive"]
    crop: str | None = None
    disease: str | None = None
    notes: str | None = None
    # optional: the expert's own advice for this disease, stored as an English DRAFT advisory for staff to verify/translate
    advice_management: str | None = None
    advice_prevention: str | None = None


class PersonRef(BaseModel):
    id: uuid.UUID
    full_name: str


class ReviewSummary(BaseModel):
    id: uuid.UUID
    case_code: str | None = None
    status: str
    needs_attention: bool
    created_at: UTCDatetime
    reviewed_at: UTCDatetime | None
    ai_crop: str
    ai_disease: str
    ai_confidence: float
    assigned_expert: PersonRef | None


class HistoryItem(BaseModel):
    action: str
    from_status: str | None
    to_status: str
    note: str | None
    actor_name: str
    created_at: UTCDatetime


class ReviewDetail(ReviewSummary):
    top_k: list[DiseaseCandidate]
    pests: list[PestDetection]
    latitude: float | None
    longitude: float | None
    expert_crop: str | None
    expert_disease: str | None
    expert_notes: str | None
    history: list[HistoryItem]


# ---------- Farmer case lookup (public, by case code) ----------
class CaseAI(BaseModel):
    crop: str
    disease: str
    confidence: float
    care: dict
    pests: list[PestDetection]


class CaseExpert(BaseModel):
    crop: str | None
    disease: str | None
    notes: str | None
    reviewed_at: UTCDatetime | None
    agrees_with_ai: bool


class CaseStatusOut(BaseModel):
    case_code: str
    submitted_at: UTCDatetime
    stage: Literal["awaiting_review", "under_review", "verified", "inconclusive"]
    message: str
    ai: CaseAI
    expert: CaseExpert | None
    final_treatment: dict | None
    treatment_note: str | None
    weather: WeatherAssessmentOut | None


# ---- Phase 4: advisories ----
class AdvisoryIn(BaseModel):
    crop: str
    disease: str
    language: Literal["en", "hi", "pa"]
    symptoms: str = ""
    prevention: str = ""
    management: str = ""
    source: str = ""
    source_url: str = ""


class AdvisoryOut(AdvisoryIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    verification_status: str
    updated_at: UTCDatetime


class ResolvedAdvisory(BaseModel):
    recommendation: str
    cultural_practice: str
    symptoms: str = ""
    language: str
    translation_pending: bool
    source: str = ""
