"""Threshold-based hotspot detection (roadmap 4.3). Pure functions, no DB / network.

A *potential hotspot* = at least `min_reports` reports of the SAME disease inside a circle of `radius_km`
within the last `window_days` days. Clusters are built greedily: take the densest circle, claim its
reports, repeat on what is left, so one outbreak is reported once instead of once per report.
A potential hotspot is NOT a confirmed outbreak: `verified_count` (expert-verified reports) is
returned separately and `confirmed` is true only when verified reports alone reach the threshold.
The thresholds are initial prototype values and must be calibrated with real data.
"""
from dataclasses import dataclass, field
from datetime import datetime
from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_KM = 6371.0088
PUBLIC_DECIMALS = 2          # ~1.1 km: coarse enough to protect a farmer's exact field location


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(a))


@dataclass(frozen=True)
class Report:
    id: str
    disease: str
    crop: str
    lat: float
    lon: float
    created_at: datetime
    verified: bool = False


@dataclass
class Hotspot:
    disease: str
    center_lat: float
    center_lon: float
    radius_km: float
    report_count: int
    verified_count: int
    confirmed: bool
    crops: list[str]
    first_report: datetime
    last_report: datetime
    report_ids: list[str] = field(default_factory=list)


def find_hotspots(reports: list[Report], min_reports: int = 5, radius_km: float = 5.0) -> list[Hotspot]:
    """`reports` must already be filtered to the time window. Returns hotspots, biggest first."""
    by_disease: dict[str, list[Report]] = {}
    for r in reports:
        by_disease.setdefault(r.disease, []).append(r)

    out: list[Hotspot] = []
    for disease, items in by_disease.items():
        remaining = list(items)
        while len(remaining) >= min_reports:
            # densest circle centred on a report; ties -> the older centre, for deterministic results
            best = None
            for c in sorted(remaining, key=lambda r: (r.created_at, r.id)):
                members = [r for r in remaining if haversine_km(c.lat, c.lon, r.lat, r.lon) <= radius_km]
                if best is None or len(members) > len(best):
                    best = members
            if best is None or len(best) < min_reports:
                break
            ids = {r.id for r in best}
            remaining = [r for r in remaining if r.id not in ids]
            verified = sum(1 for r in best if r.verified)
            out.append(Hotspot(
                disease=disease,
                center_lat=round(sum(r.lat for r in best) / len(best), PUBLIC_DECIMALS),
                center_lon=round(sum(r.lon for r in best) / len(best), PUBLIC_DECIMALS),
                radius_km=radius_km, report_count=len(best), verified_count=verified,
                confirmed=verified >= min_reports,
                crops=sorted({r.crop for r in best}),
                first_report=min(r.created_at for r in best), last_report=max(r.created_at for r in best),
                report_ids=sorted(ids),
            ))
    return sorted(out, key=lambda h: (-h.report_count, h.disease))
