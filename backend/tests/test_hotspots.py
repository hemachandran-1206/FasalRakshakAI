import os
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["LOAD_MODELS_ON_STARTUP"] = "false"
from datetime import datetime, timedelta, timezone

from app.services import hotspots as hs

NOW = datetime(2026, 11, 7, tzinfo=timezone.utc)


def rep(i, disease="Late Blight", lat=30.97, lon=76.52, verified=False, crop="Potato"):
    return hs.Report(f"r{i}", disease, crop, lat, lon, NOW - timedelta(hours=i), verified)


def test_haversine_known_distance():
    assert abs(hs.haversine_km(30.0, 76.0, 30.1, 76.0) - 11.12) < 0.05      # 0.1 deg latitude ~ 11.12 km


def test_threshold_exact_and_below():
    assert len(hs.find_hotspots([rep(i) for i in range(5)], 5, 5)) == 1
    assert hs.find_hotspots([rep(i) for i in range(4)], 5, 5) == []


def test_radius_matters_and_far_reports_do_not_join():
    near = [rep(i, lat=30.97 + i * 0.005) for i in range(5)]        # all within ~2.2 km
    assert len(hs.find_hotspots(near, 5, 5)) == 1
    spread = [rep(i, lat=30.97 + i * 0.1) for i in range(5)]        # ~11 km apart each
    assert hs.find_hotspots(spread, 5, 5) == []


def test_diseases_are_grouped_separately():
    mixed = [rep(i, "Late Blight") for i in range(3)] + [rep(10 + i, "Early Blight") for i in range(3)]
    assert hs.find_hotspots(mixed, 5, 5) == []


def test_two_distant_clusters_and_no_double_counting():
    a = [rep(i) for i in range(6)]
    b = [rep(20 + i, lat=31.5, lon=77.0) for i in range(5)]
    found = hs.find_hotspots(a + b, 5, 5)
    assert [h.report_count for h in found] == [6, 5]
    assert set(found[0].report_ids).isdisjoint(found[1].report_ids)


def test_confirmed_needs_verified_reports_and_coords_are_rounded():
    reports = [rep(i, verified=i < 2) for i in range(5)]
    h = hs.find_hotspots(reports, 5, 5)[0]
    assert h.verified_count == 2 and h.confirmed is False
    assert h.center_lat == round(h.center_lat, 2)
    assert hs.find_hotspots([rep(i, verified=True) for i in range(5)], 5, 5)[0].confirmed is True
