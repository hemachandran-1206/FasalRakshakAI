from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://hs202:hs202@localhost:5432/hs202"
    upload_dir: Path = BACKEND_DIR / "uploads"
    max_upload_mb: int = 10
    confidence_threshold: float = 70.0   # at/above: may be shown as 'diagnosed' (if a crop was chosen and the photo is OK)
    likely_threshold: float = 40.0       # below this the AI does not guess: straight to an expert
    cors_origins: str = "http://localhost:5173"   # comma-separated; React/Vite dev server
    load_models_on_startup: bool = True
    open_meteo_url: str = "https://api.open-meteo.com/v1/forecast"
    weather_timeout_s: float = 10.0
    trust_proxy_headers: bool = False   # True when hosted behind a proxy (uses X-Forwarded-For for rate limits)
    environment: str = "dev"            # set ENVIRONMENT=production when hosted
    jwt_secret: str = "dev-only-secret-change-me-0123456789abcdef"
    access_token_minutes: int = 480
    hotspot_min_reports: int = 5       # roadmap 4.3 initial values
    hotspot_radius_km: float = 5.0
    hotspot_window_days: int = 7
    hotspot_min_confidence: float = 50.0   # extra: ignore weak unverified AI guesses


settings = Settings()
