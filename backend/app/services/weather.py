"""Open-Meteo client (free, no API key, non-commercial use). Returns the last 7 days of hourly data."""
from datetime import datetime, timezone

import httpx

from ..config import settings
from .risk_rules import Assessment, HourlyObs, InsufficientData, WINDOW_HOURS, evaluate

__all__ = ["WeatherUnavailable", "InsufficientData", "parse_hourly", "fetch_hourly", "assess"]


class WeatherUnavailable(Exception):
    pass


def parse_hourly(data: dict, now: datetime) -> list[HourlyObs]:
    """Open-Meteo JSON (timezone=GMT) -> hourly observations up to `now`, oldest first."""
    try:
        h = data["hourly"]
        rows = zip(h["time"], h["temperature_2m"], h["relative_humidity_2m"], h["precipitation"])
        obs = []
        for t, temp, rh, p in rows:
            ts = datetime.fromisoformat(t).replace(tzinfo=timezone.utc)
            if ts <= now:
                obs.append(HourlyObs(ts, temp, rh, p))
    except (KeyError, TypeError, ValueError) as e:
        raise WeatherUnavailable(f"unexpected Open-Meteo response: {e}") from e
    return obs[-WINDOW_HOURS:]


async def fetch_hourly(latitude: float, longitude: float) -> list[HourlyObs]:
    params = {
        "latitude": latitude, "longitude": longitude,
        "hourly": "temperature_2m,relative_humidity_2m,precipitation",
        "past_days": 7, "forecast_days": 1, "timezone": "GMT",
    }
    try:
        async with httpx.AsyncClient(timeout=settings.weather_timeout_s) as client:
            resp = await client.get(settings.open_meteo_url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, ValueError) as e:
        raise WeatherUnavailable(f"Open-Meteo request failed: {e}") from e
    return parse_hourly(data, datetime.now(timezone.utc))


async def assess(latitude: float, longitude: float) -> Assessment:
    return evaluate(await fetch_hourly(latitude, longitude))
