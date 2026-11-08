from fastapi import APIRouter, HTTPException, Query

from ..schemas import WeatherAssessmentOut
from ..services import weather as weather_service

router = APIRouter(tags=["weather"])


@router.get("/weather-risk", response_model=WeatherAssessmentOut)
async def weather_risk(latitude: float = Query(..., ge=-90, le=90), longitude: float = Query(..., ge=-180, le=180)):
    """Disease-risk assessment for a location from the last 7 days of weather (no detection needed)."""
    try:
        result = await weather_service.assess(latitude, longitude)
    except (weather_service.WeatherUnavailable, weather_service.InsufficientData) as e:
        raise HTTPException(503, f"Weather data unavailable: {e}")
    return WeatherAssessmentOut.model_validate(result, from_attributes=True)
