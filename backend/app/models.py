"""The six tables from the roadmap (section 6)."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120), default="")
    role: Mapped[str] = mapped_column(String(16), default="farmer")        # farmer | expert | admin
    preferred_language: Mapped[str] = mapped_column(String(8), default="en")  # en | hi | pa
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Detection(Base):
    __tablename__ = "detections"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    case_code: Mapped[str | None] = mapped_column(String(12), unique=True, index=True, nullable=True)  # farmer-facing key
    image_path: Mapped[str] = mapped_column(String(500))
    crop: Mapped[str] = mapped_column(String(80), index=True)
    disease: Mapped[str] = mapped_column(String(120), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    top_k: Mapped[list] = mapped_column(JSON, default=list)        # all disease candidates returned by the model
    pests: Mapped[list] = mapped_column(JSON, default=list)        # YOLO detections with boxes
    care_status: Mapped[str] = mapped_column(String(16))           # healthy | diagnosed | likely | escalated
    triage: Mapped[dict] = mapped_column(JSON, default=dict)       # reason, crop_selected, photo warnings
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)

    review: Mapped["ExpertReview"] = relationship(back_populates="detection", uselist=False)
    weather_risks: Mapped[list["WeatherRisk"]] = relationship(back_populates="detection")


class WeatherRisk(Base):
    __tablename__ = "weather_risks"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    detection_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("detections.id"), index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    rainfall_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw: Mapped[dict] = mapped_column(JSON, default=dict)          # raw Open-Meteo payload used for the rule
    disease: Mapped[str] = mapped_column(String(120))              # disease this rule is about (independent of image result)
    risk_level: Mapped[str] = mapped_column(String(16))            # low | moderate | high
    rule_id: Mapped[str] = mapped_column(String(80), default="")
    explanation: Mapped[str] = mapped_column(Text, default="")

    detection: Mapped[Detection] = relationship(back_populates="weather_risks")


class ExpertReview(Base):
    __tablename__ = "expert_reviews"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    detection_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("detections.id"), unique=True)
    assigned_expert_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)  # pending|assigned|confirmed|corrected|inconclusive
    needs_attention: Mapped[bool] = mapped_column(Boolean, default=False)           # low confidence / no knowledge-base entry
    # the AI prediction lives on `detections` and is never overwritten; the expert's answer is stored here
    expert_crop: Mapped[str | None] = mapped_column(String(80), nullable=True)
    expert_disease: Mapped[str | None] = mapped_column(String(120), nullable=True)
    expert_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    detection: Mapped[Detection] = relationship(back_populates="review")
    history: Mapped[list["ReviewHistory"]] = relationship(back_populates="review", order_by="ReviewHistory.created_at")


class ReviewHistory(Base):
    __tablename__ = "review_history"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    review_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("expert_reviews.id"), index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)  # null = system
    action: Mapped[str] = mapped_column(String(32))                # created | assigned | confirmed | corrected | inconclusive
    from_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    to_status: Mapped[str] = mapped_column(String(16))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    review: Mapped[ExpertReview] = relationship(back_populates="history")


class Advisory(Base):
    __tablename__ = "advisories"
    __table_args__ = (
        UniqueConstraint("crop", "disease", "language", name="uq_advisory_crop_disease_lang"),
        Index("ix_advisory_lookup", "crop", "disease", "language", "verification_status"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    crop: Mapped[str] = mapped_column(String(80))
    disease: Mapped[str] = mapped_column(String(120))
    language: Mapped[str] = mapped_column(String(8), default="en")
    symptoms: Mapped[str] = mapped_column(Text, default="")
    prevention: Mapped[str] = mapped_column(Text, default="")
    management: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(300), default="")
    source_url: Mapped[str] = mapped_column(String(500), default="")
    verification_status: Mapped[str] = mapped_column(String(16), default="draft")  # draft | verified
    verified_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
