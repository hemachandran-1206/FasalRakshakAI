import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from app import db as dbmod
from app.main import app
from app.models import Detection, ExpertReview, ReviewHistory, User
from app.services import cases, security

PW = "correct-horse-battery"


def make(crop="Potato", disease="Late Blight", conf=90.0, status="pending", expert_crop=None, expert_disease=None,
         notes=None, code="K7M2QX9P"):
    with dbmod.SessionLocal() as s:
        d = Detection(case_code=code, image_path="secret/path.jpg", crop=crop, disease=disease, confidence=conf,
                      top_k=[], pests=[{"pest": "aphid", "confidence": 80.0, "bbox_xyxy": [1, 2, 3, 4]}],
                      care_status="diagnosed", latitude=30.97123, longitude=76.52456)
        d.review = ExpertReview(status=status, expert_crop=expert_crop, expert_disease=expert_disease, expert_notes=notes)
        s.add(d); s.commit()


@pytest.fixture
def c():
    return TestClient(app)


def test_code_format_and_normalisation():
    code = "".join(cases.ALPHABET[:8])
    assert cases.format_code("K7M2QX9P") == "K7M2-QX9P"
    for typed in ("k7m2-qx9p", " K7M2 QX9P ", "K7M2QX9P", "k7m2_qx9p"):
        assert cases.normalise(typed) == "K7M2QX9P"
    assert not set("01ILO") & set(cases.ALPHABET) and len(code) == 8
    with dbmod.SessionLocal() as s:
        generated = {cases.unique_code(s) for _ in range(200)}
    assert len(generated) == 200 and all(len(g) == 8 and set(g) <= set(cases.ALPHABET) for g in generated)


def test_unknown_or_malformed_code_is_404(c):
    make()
    assert c.get("/api/cases/ZZZZ-ZZZZ").status_code == 404
    assert c.get("/api/cases/abc").status_code == 404
    assert c.get("/api/cases/K7M2-QX9").status_code == 404


def test_pending_then_assigned_show_ai_result_and_treatment(c):
    make()
    r = c.get("/api/cases/k7m2 qx9p").json()
    assert r["case_code"] == "K7M2-QX9P" and r["stage"] == "awaiting_review"
    assert r["ai"]["care"]["status"] == "diagnosed" and "fungicide" in r["ai"]["care"]["recommendation"]
    assert r["expert"] is None and r["final_treatment"] is None
    with dbmod.SessionLocal() as s:
        s.query(ExpertReview).update({"status": "assigned"}); s.commit()
    assert c.get("/api/cases/K7M2-QX9P").json()["stage"] == "under_review"


def test_verified_confirm_and_correction_with_and_without_stored_treatment(c):
    make(status="confirmed", expert_crop="Potato", expert_disease="Late Blight", notes="matches")
    r = c.get("/api/cases/K7M2-QX9P").json()
    assert r["stage"] == "verified" and r["expert"]["agrees_with_ai"] is True
    assert r["final_treatment"]["disease"] == "Late Blight" and r["expert"]["notes"] == "matches"

    with dbmod.SessionLocal() as s:
        s.query(ExpertReview).update({"status": "corrected", "expert_crop": "Tomato", "expert_disease": "Septoria Leaf Spot"}); s.commit()
    r = c.get("/api/cases/K7M2-QX9P").json()
    assert r["expert"]["agrees_with_ai"] is False and r["final_treatment"]["crop"] == "Tomato"   # NOT the AI's potato advice

    with dbmod.SessionLocal() as s:
        s.query(ExpertReview).update({"expert_disease": "Some Rare Disease"}); s.commit()
    r = c.get("/api/cases/K7M2-QX9P").json()
    assert r["final_treatment"] is None and "KVK" in r["treatment_note"]

    with dbmod.SessionLocal() as s:
        s.query(ExpertReview).update({"expert_disease": "Healthy"}); s.commit()
    assert "no disease" in c.get("/api/cases/K7M2-QX9P").json()["treatment_note"]


def test_inconclusive_shows_reason(c):
    make(status="inconclusive", notes="photo too blurry")
    r = c.get("/api/cases/K7M2-QX9P").json()
    assert r["stage"] == "inconclusive" and r["expert"]["notes"] == "photo too blurry" and "KVK" in r["message"]


def test_public_view_never_leaks_private_fields(c):
    make(status="corrected", expert_crop="Tomato", expert_disease="Early Blight")
    with dbmod.SessionLocal() as s:
        u = User(email="e@x.org", role="expert", full_name="Dr Secret Name", password_hash=security.hash_password(PW)); s.add(u); s.commit()
        s.query(ExpertReview).update({"assigned_expert_id": u.id}); s.commit()
    body = c.get("/api/cases/K7M2-QX9P").text
    for secret in ("30.97", "76.52", "secret/path", "Dr Secret Name", "e@x.org", "image_path", "latitude", "assigned"):
        assert secret not in body


def test_lookups_are_rate_limited(c):
    make()
    codes = [c.get("/api/cases/AAAA-AAAA").status_code for _ in range(31)]
    assert codes[:30] == [404] * 30 and codes[30] == 429
    assert c.get("/api/cases/K7M2-QX9P").status_code == 429       # real code is blocked too while limited


def test_migration_adds_and_backfills_case_code_on_old_database():
    from sqlalchemy.orm import Session
    from app.migrations import ensure_schema
    old = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    with old.begin() as conn:       # a Phase-2-era table without case_code
        conn.execute(text("CREATE TABLE detections (id CHAR(32) PRIMARY KEY, user_id CHAR(32), image_path VARCHAR(500), crop VARCHAR(80), "
                          "disease VARCHAR(120), confidence FLOAT, top_k JSON, pests JSON, care_status VARCHAR(16), latitude FLOAT, "
                          "longitude FLOAT, created_at DATETIME)"))
        for _ in range(3):
            conn.execute(text("INSERT INTO detections (id, image_path, crop, disease, confidence, top_k, pests, care_status, created_at) "
                              "VALUES (:i, 'x', 'Potato', 'Late Blight', 90, '[]', '[]', 'diagnosed', '2026-11-01 00:00:00')"), {"i": uuid.uuid4().hex})
    ensure_schema(old)
    ensure_schema(old)              # idempotent
    with Session(old) as db:
        codes = [d.case_code for d in db.query(Detection)]
    assert len(codes) == 3 and len(set(codes)) == 3 and all(codes)
