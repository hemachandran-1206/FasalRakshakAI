from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from app import db as dbmod
from app.main import app
from app.models import Detection, ExpertReview


def add(disease="Late Blight", conf=90.0, hours=2, lat=30.97123, lon=76.52456, review=None):
    with dbmod.SessionLocal() as s:
        d = Detection(image_path="x", crop="Potato", disease=disease, confidence=conf, top_k=[], pests=[],
                      care_status="diagnosed", latitude=lat, longitude=lon,
                      created_at=datetime.now(timezone.utc) - timedelta(hours=hours))
        d.review = ExpertReview(status=review or "pending", expert_disease="Early Blight" if review == "corrected" else None)
        s.add(d); s.commit()


def reset():
    with dbmod.SessionLocal() as s:
        s.query(ExpertReview).delete(); s.query(Detection).delete(); s.commit()


def test_hotspot_endpoint_filters_and_rounds():
    reset()
    for _ in range(5): add()
    add(disease="Healthy"); add(conf=20.0); add(hours=24 * 10)      # healthy / weak guess / too old -> ignored
    add(lat=None, lon=None)                                          # no GPS -> ignored
    c = TestClient(app)
    r = c.get("/api/hotspots").json()
    assert len(r["hotspots"]) == 1 and r["hotspots"][0]["report_count"] == 5
    assert r["hotspots"][0]["latitude"] == 30.97 and r["parameters"]["min_reports"] == 5
    pts = c.get("/api/reports").json()
    assert len(pts) == 5 and pts[0]["latitude"] == 30.97 and pts[0]["longitude"] == 76.52   # rounded, no ids/images


def test_expert_correction_changes_the_disease_used():
    reset()
    for _ in range(5): add(review="corrected")
    h = TestClient(app).get("/api/hotspots").json()["hotspots"][0]
    assert h["disease"] == "Early Blight" and h["verified_count"] == 5 and h["confirmed"] is True


def test_parameter_validation():
    c = TestClient(app)
    assert c.get("/api/hotspots", params={"min_reports": 1}).status_code == 422
    assert c.get("/api/hotspots", params={"radius_km": 0}).status_code == 422
