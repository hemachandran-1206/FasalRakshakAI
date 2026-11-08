import os
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("LOAD_MODELS_ON_STARTUP", "false")

from fastapi.testclient import TestClient

from app.main import app
from app.services import risk_rules as rr
from app.services import weather as w


def test_weather_endpoint_ok_and_validation_and_503(monkeypatch):
    async def ok(lat, lon):
        from tests.test_risk_rules import obs
        return rr.evaluate(obs(18, 95))
    monkeypatch.setattr(w, "assess", ok)
    c = TestClient(app)
    r = c.get("/api/weather-risk", params={"latitude": 30.97, "longitude": 76.52})
    assert r.status_code == 200 and r.json()["risks"][0]["risk_level"] == "high"
    assert c.get("/api/weather-risk", params={"latitude": 95, "longitude": 0}).status_code == 422

    async def down(lat, lon):
        raise w.WeatherUnavailable("down")
    monkeypatch.setattr(w, "assess", down)
    assert c.get("/api/weather-risk", params={"latitude": 30.97, "longitude": 76.52}).status_code == 503
