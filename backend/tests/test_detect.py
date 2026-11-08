import io

from fastapi.testclient import TestClient
from PIL import Image

from app import db as dbmod
from app.main import app
from app.models import Detection, ExpertReview, ReviewHistory, WeatherRisk  # noqa: E402
from app.services import weather as weather_service  # noqa: E402
from app.services import risk_rules  # noqa: E402
import pytest  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402


def _obs(temp, rh, n=168):
    now = datetime.now(timezone.utc)
    return [risk_rules.HourlyObs(now - timedelta(hours=n - i), temp, rh, 0.1) for i in range(n)]


@pytest.fixture(autouse=True)
def fake_weather(monkeypatch):
    async def fake_assess(lat, lon):
        return risk_rules.evaluate(_obs(18.0, 95.0))      # wet + cool -> high late-blight risk
    monkeypatch.setattr(weather_service, "assess", fake_assess)


class StubPipeline:
    def __init__(self, diseases, pests=()):
        self.diseases, self.pests = diseases, list(pests)
    def predict_disease(self, image, top_k=3, crop=None):
        self.last_crop = crop
        return self.diseases
    def predict_pests(self, image, conf=0.25):
        return self.pests


def _png(size=300, noisy=True):
    import random
    rnd = random.Random(1)
    im = Image.new("RGB", (size, size), "green")
    if noisy:   # random texture => high Laplacian variance => not flagged as blurry
        im.putdata([(rnd.randrange(256), rnd.randrange(256), rnd.randrange(256)) for _ in range(size * size)])
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def _client(diseases, pests=()):
    app.state.pipeline = StubPipeline(diseases, pests)
    return TestClient(app)


def test_confident_diagnosis_creates_detection_and_pending_review():
    c = _client([{"plant": "Potato", "disease": "Late Blight", "confidence": 94.0}],
                [{"pest": "aphid", "confidence": 80.0, "bbox_xyxy": [1, 2, 3, 4]}])
    with c:
        r = c.post("/api/detect", files={"file": ("l.png", _png(), "image/png")},
                   data={"latitude": "30.97", "longitude": "76.52", "crop": "potato"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["care_status"] == "diagnosed" and body["review_status"] == "pending"
    assert body["care"]["recommendation"] and body["pests"][0]["pest"] == "aphid"
    with dbmod.SessionLocal() as s:
        review = s.query(ExpertReview).one()
        assert review.needs_attention is False
        assert s.query(ReviewHistory).one().action == "created"


def test_low_confidence_is_escalated_and_flagged():
    c = _client([{"plant": "Tomato", "disease": "Early Blight", "confidence": 31.0}])
    with c:
        r = c.post("/api/detect", files={"file": ("l.png", _png(), "image/png")})
    assert r.json()["care_status"] == "escalated"
    with dbmod.SessionLocal() as s:
        assert s.query(ExpertReview).filter_by(needs_attention=True).count() == 1


def test_healthy_and_get_detection():
    c = _client([{"plant": "Tomato", "disease": "Healthy", "confidence": 99.0}])
    with c:
        det_id = c.post("/api/detect", files={"file": ("l.png", _png(), "image/png")}, data={"crop": "tomato"}).json()["id"]
        r = c.get(f"/api/detections/{det_id}")
    assert r.status_code == 200 and r.json()["care_status"] == "healthy"


def test_rejects_bad_input():
    c = _client([{"plant": "Tomato", "disease": "Healthy", "confidence": 99.0}])
    with c:
        assert c.post("/api/detect", files={"file": ("x.txt", b"hi", "text/plain")}).status_code == 415
        assert c.post("/api/detect", files={"file": ("x.png", b"notimage", "image/png")}).status_code == 422
        ok = ("l.png", _png(), "image/png")
        assert c.post("/api/detect", files={"file": ok}, data={"latitude": "30"}).status_code == 422
        assert c.post("/api/detect", files={"file": ok}, data={"latitude": "95", "longitude": "10"}).status_code == 422
        assert c.get("/api/detections/00000000-0000-0000-0000-000000000000").status_code == 404


def test_weather_risk_is_stored_and_returned_when_gps_given():
    c = _client([{"plant": "Potato", "disease": "Late Blight", "confidence": 94.0}])
    with c:
        r = c.post("/api/detect", files={"file": ("l.png", _png(), "image/png")},
                   data={"latitude": "30.97", "longitude": "76.52", "crop": "potato"})
        det_id = r.json()["id"]
        again = c.get(f"/api/detections/{det_id}").json()
    assert r.json()["weather"]["risks"][0]["risk_level"] == "high"
    assert again["weather"]["risks"][0]["rule_id"] == "late_blight_jhulsacast_punjab"
    with dbmod.SessionLocal() as s:
        assert s.query(WeatherRisk).filter_by(detection_id=__import__("uuid").UUID(det_id)).count() == 1


def test_no_weather_without_gps_and_weather_failure_does_not_block_detection(monkeypatch):
    c = _client([{"plant": "Potato", "disease": "Late Blight", "confidence": 94.0}])
    with c:
        assert c.post("/api/detect", files={"file": ("l.png", _png(), "image/png")}).json()["weather"] is None

        async def boom(lat, lon):
            raise weather_service.WeatherUnavailable("network down")
        monkeypatch.setattr(weather_service, "assess", boom)
        r = c.post("/api/detect", files={"file": ("l.png", _png(), "image/png")},
                   data={"latitude": "30.97", "longitude": "76.52"})
    assert r.status_code == 201 and r.json()["weather"] is None


def test_detect_returns_a_case_code_that_works_on_the_lookup_page():
    c = _client([{"plant": "Potato", "disease": "Late Blight", "confidence": 94.0}])
    with c:
        code = c.post("/api/detect", files={"file": ("l.png", _png(), "image/png")}, data={"crop": "potato"}).json()["case_code"]
        looked_up = c.get(f"/api/cases/{code.lower()}").json()
    import re
    assert re.fullmatch(r"[2-9A-HJKMNP-Z]{4}-[2-9A-HJKMNP-Z]{4}", code)
    assert looked_up["case_code"] == code and looked_up["stage"] == "awaiting_review"


# ---------- Phase 3c: crop-aware triage ----------
POTATO_LB = [{"plant": "Potato", "disease": "Late Blight", "confidence": 94.0},
             {"plant": "Potato", "disease": "Early Blight", "confidence": 4.0}]


def _post(c, diseases, **data):
    return c.post("/api/detect", files={"file": ("l.png", _png(), "image/png")}, data=data)


def test_crop_choice_is_passed_to_the_model_as_a_restriction():
    c = _client(POTATO_LB)
    with c:
        r = _post(c, POTATO_LB, crop="potato")
    assert r.json()["care_status"] == "diagnosed" and app.state.pipeline.last_crop == "Potato"


def test_without_a_crop_even_a_confident_result_is_only_likely():
    c = _client(POTATO_LB)
    with c:
        r = _post(c, POTATO_LB).json()
    assert r["care_status"] == "likely" and r["care"]["reason"] == "crop_not_selected"
    assert r["care"]["candidates"][0]["disease"] == "Late Blight" and "KVK" in r["care"]["interim_advice"]
    assert app.state.pipeline.last_crop is None
    with c:
        assert _post(c, POTATO_LB, crop="not_sure").json()["care_status"] == "likely"


def test_unsupported_crop_skips_the_disease_model_and_goes_to_an_expert():
    c = _client(POTATO_LB, [{"pest": "aphid", "confidence": 80.0, "bbox_xyxy": [1, 2, 3, 4]}])
    app.state.pipeline.last_crop = "untouched"
    with c:
        r = _post(c, POTATO_LB, crop="rice")
        body = r.json()
    assert r.status_code == 201 and body["care_status"] == "escalated" and body["disease"] == "Not assessed by AI"
    assert "Rice" in body["care"]["message"] and body["top_k"] == [] and body["pests"][0]["pest"] == "aphid"
    assert app.state.pipeline.last_crop == "untouched"             # predict_disease was never called
    with dbmod.SessionLocal() as s:
        assert s.query(ExpertReview).one().needs_attention is True


def test_medium_low_and_unknown_cases():
    c = _client([{"plant": "Tomato", "disease": "Early Blight", "confidence": 55.0}])
    with c:
        assert _post(c, None, crop="tomato").json()["care_status"] == "likely"
    c = _client([{"plant": "Tomato", "disease": "Early Blight", "confidence": 25.0}])
    with c:
        assert _post(c, None, crop="tomato").json()["care_status"] == "escalated"
    c = _client([{"plant": "Tomato", "disease": "Healthy", "confidence": 55.0}])
    with c:
        assert _post(c, None, crop="tomato").json()["care_status"] == "likely"       # 'healthy' needs high confidence
    c = _client([{"plant": "Tomato", "disease": "Healthy", "confidence": 95.0}])
    with c:
        assert _post(c, None, crop="tomato").json()["care_status"] == "healthy"
        assert _post(c, None, crop="martian-moss").status_code == 422


def test_photo_quality_rules():
    c = _client(POTATO_LB)
    with c:
        tiny = c.post("/api/detect", files={"file": ("t.png", _png(64), "image/png")}, data={"crop": "potato"})
        assert tiny.status_code == 422 and "too small" in tiny.json()["detail"]
        flat = c.post("/api/detect", files={"file": ("f.png", _png(300, noisy=False), "image/png")}, data={"crop": "potato"}).json()
    assert any("blurry" in w for w in flat["warnings"])
    assert flat["care_status"] == "likely" and flat["care"]["reason"] == "poor_photo"     # a poor photo caps a confident result


def test_unassessed_reports_do_not_create_hotspots_until_an_expert_names_the_disease():
    c = _client(POTATO_LB)
    with c:
        for _ in range(5):
            _post(c, None, crop="rice", latitude="30.97", longitude="76.52")
        assert c.get("/api/hotspots").json()["hotspots"] == []
