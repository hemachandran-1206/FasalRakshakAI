from datetime import datetime, timedelta, timezone

import pytest

from app.services import risk_rules as rr
from app.services import weather as w


def obs(temp, rh, n=168, precip=0.0):
    now = datetime(2026, 11, 7, tzinfo=timezone.utc)
    return [rr.HourlyObs(now - timedelta(hours=n - i), temp, rh, precip) for i in range(n)]


def level(o):
    return rr.late_blight_jhulsacast(o).risk_level


def test_high_when_both_thresholds_met():
    assert level(obs(18, 95)) == "high"


def test_low_when_dry_or_too_cold_or_too_hot():
    assert level(obs(18, 50)) == "low"       # RH criterion fails
    assert level(obs(2, 95)) == "low"        # below 7.2 C
    assert level(obs(32, 95)) == "low"       # above 26.6 C


def test_exact_thresholds_are_inclusive():
    o = obs(18, 95)
    # exactly 90 h of RH>=85 and exactly 115 h in the temperature band
    o = [rr.HourlyObs(x.time, 18 if i < 115 else 30, 85 if i < 90 else 84.9, 0) for i, x in enumerate(o)]
    assert level(o) == "high"
    o2 = [rr.HourlyObs(x.time, x.temp_c, 85 if i < 89 else 84.9, 0) for i, x in enumerate(o)]
    assert level(o2) == "moderate"           # 89 h < 90 but >= 60 % of the threshold


def test_temperature_band_edges():
    assert level(obs(7.2, 95)) == "high" and level(obs(26.6, 95)) == "high"
    assert level(obs(7.1, 95)) == "low" and level(obs(26.7, 95)) == "low"


def test_moderate_band():
    o = [rr.HourlyObs(x.time, 18, 90 if i < 60 else 50, 0) for i, x in enumerate(obs(18, 95))]
    assert level(o) == "moderate"            # 60 h RH (>= 54) and 168 h temp


def test_evaluate_summary_and_refuses_thin_data():
    a = rr.evaluate(obs(18, 95, precip=0.5))
    assert a.temperature_c == 18 and a.humidity_pct == 95 and a.rainfall_7d_mm == 84.0
    assert "does not confirm" in a.risks[0].explanation
    with pytest.raises(rr.InsufficientData):
        rr.evaluate(obs(18, 95, n=100))
    holes = [rr.HourlyObs(x.time, None, None, None) for x in obs(18, 95)]
    with pytest.raises(rr.InsufficientData):
        rr.evaluate(holes)


def test_parse_open_meteo_payload_cuts_future_and_handles_bad_json():
    now = datetime(2026, 11, 7, 12, tzinfo=timezone.utc)
    times = [(now + timedelta(hours=i - 200)).strftime("%Y-%m-%dT%H:%M") for i in range(230)]
    n = len(times)
    data = {"hourly": {"time": times, "temperature_2m": [20.0] * n,
                       "relative_humidity_2m": [80] * n, "precipitation": [0.0] * n}}
    parsed = w.parse_hourly(data, now)
    assert len(parsed) == 168 and parsed[-1].time == now
    with pytest.raises(w.WeatherUnavailable):
        w.parse_hourly({"nope": 1}, now)
