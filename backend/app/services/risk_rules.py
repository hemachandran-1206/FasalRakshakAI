"""Weather -> disease-risk rules. Pure functions (no network, no DB) so they are easy to test.

Rule 1: potato/tomato LATE BLIGHT, ICAR-CPRI JHULSACAST (Punjab calibration).
  Both must hold within the last 7 days (168 h):
    - at least 90 h with relative humidity >= 85 %
    - at least 115 h with temperature between 7.2 and 26.6 C
  -> late blight appearance is predicted within ~10 days (if inoculum is present).
Sources: ICAR Potato Journal, "Forecasting late blight of potato in Punjab using JHULSACAST model"
         https://epubs.icar.org.in/index.php/PotatoJ/article/view/32182
         ICAR-CPRI late blight forecasting notes https://cpri.icar.gov.in/AddLink/getIMG/6065
Caveats (shown to the user, kept in the explanation):
  - the models were built for potato; tomato late blight is the same pathogen (Phytophthora infestans),
    so the rule is applied to tomato too, but it is NOT separately validated for tomato.
  - the 'moderate' band (>= 60 % of both thresholds) is a prototype setting, not from the papers.
  - Open-Meteo gives gridded model data (~10 km), not readings from a field station.
"""
from dataclasses import dataclass, field
from datetime import datetime

WINDOW_HOURS = 168            # 7 days
MIN_VALID_HOURS = 120         # fewer valid hours than this -> refuse to judge

RH_MIN = 85.0
TEMP_MIN, TEMP_MAX = 7.2, 26.6
RH_HOURS_REQUIRED = 90
TEMP_HOURS_REQUIRED = 115
MODERATE_FRACTION = 0.6       # prototype setting

LATE_BLIGHT_SOURCE = "https://epubs.icar.org.in/index.php/PotatoJ/article/view/32182"


class InsufficientData(Exception):
    pass


@dataclass(frozen=True)
class HourlyObs:
    time: datetime
    temp_c: float | None
    rh_pct: float | None
    precip_mm: float | None


@dataclass
class RiskResult:
    disease: str
    crops: list[str]
    rule_id: str
    risk_level: str            # low | moderate | high
    explanation: str
    source_url: str
    metrics: dict = field(default_factory=dict)


@dataclass
class Assessment:
    temperature_c: float | None
    humidity_pct: float | None
    rainfall_7d_mm: float
    risks: list[RiskResult]


def late_blight_jhulsacast(window: list[HourlyObs]) -> RiskResult:
    valid = [o for o in window if o.temp_c is not None and o.rh_pct is not None]
    rh_hours = sum(1 for o in valid if o.rh_pct >= RH_MIN)
    temp_hours = sum(1 for o in valid if TEMP_MIN <= o.temp_c <= TEMP_MAX)

    if rh_hours >= RH_HOURS_REQUIRED and temp_hours >= TEMP_HOURS_REQUIRED:
        level = "high"
    elif (rh_hours >= MODERATE_FRACTION * RH_HOURS_REQUIRED
          and temp_hours >= MODERATE_FRACTION * TEMP_HOURS_REQUIRED):
        level = "moderate"
    else:
        level = "low"

    meaning = {
        "high": "Both ICAR-CPRI JHULSACAST criteria are met: conditions are favourable for late blight, "
                "which is predicted to appear within about 10 days if the pathogen is present.",
        "moderate": "Conditions are approaching the JHULSACAST thresholds (prototype 'moderate' band); keep monitoring.",
        "low": "Conditions are below the JHULSACAST thresholds for late blight.",
    }[level]
    explanation = (
        f"Last 7 days: {rh_hours} h with RH >= {RH_MIN:.0f}% (threshold {RH_HOURS_REQUIRED} h) and "
        f"{temp_hours} h between {TEMP_MIN} and {TEMP_MAX} C (threshold {TEMP_HOURS_REQUIRED} h). {meaning} "
        "This shows favourable weather only; it does not confirm that the disease is present."
    )
    return RiskResult(
        disease="Late Blight", crops=["Potato", "Tomato"], rule_id="late_blight_jhulsacast_punjab",
        risk_level=level, explanation=explanation, source_url=LATE_BLIGHT_SOURCE,
        metrics={"rh_hours": rh_hours, "rh_hours_required": RH_HOURS_REQUIRED,
                 "temp_hours": temp_hours, "temp_hours_required": TEMP_HOURS_REQUIRED,
                 "valid_hours": len(valid), "window_hours": len(window)},
    )


RULES = [late_blight_jhulsacast]


def evaluate(obs: list[HourlyObs]) -> Assessment:
    """obs: hourly observations in time order, last one = now. Uses the most recent 168 h."""
    window = obs[-WINDOW_HOURS:]
    if sum(1 for o in window if o.temp_c is not None and o.rh_pct is not None) < MIN_VALID_HOURS:
        raise InsufficientData(f"fewer than {MIN_VALID_HOURS} valid hourly records in the last 7 days")
    latest = next((o for o in reversed(window) if o.temp_c is not None and o.rh_pct is not None), None)
    return Assessment(
        temperature_c=latest.temp_c if latest else None,
        humidity_pct=latest.rh_pct if latest else None,
        rainfall_7d_mm=round(sum(o.precip_mm or 0.0 for o in window), 1),
        risks=[rule(window) for rule in RULES],
    )
