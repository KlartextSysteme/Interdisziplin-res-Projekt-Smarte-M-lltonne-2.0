from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./smart_bin.db"
    admin_token: str = "changeme"
    anthropic_api_key: str = ""
    groq_api_key: str = ""
    cors_origins: list[str] = ["*"]

    # Routing (OSRM public demo by default)
    osrm_base_url: str = "https://router.project-osrm.org"

    # Depot / truck home base (Gewerbegebiet nahe FH Südwestfalen)
    depot_lat: float = 51.5583
    depot_lng: float = 8.1303
    depot_name: str = "Betriebshof Doyenweg"

    class Config:
        env_file = ".env"


settings = Settings()
