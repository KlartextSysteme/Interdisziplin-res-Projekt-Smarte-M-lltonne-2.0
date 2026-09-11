from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./smart_bin.db"
    admin_token: str = "changeme"
    groq_api_key: str = ""
    cors_origins: list[str] = ["*"]

    # Routing (OSRM public demo by default)
    osrm_base_url: str = "https://router.project-osrm.org"

    # Depot / truck home base (Gewerbegebiet nahe FH Südwestfalen)
    depot_lat: float = 51.5583
    depot_lng: float = 8.1303
    depot_name: str = "Betriebshof Doyenweg"

    # Müllwagen: gemeinsame Wahrheit für Planung *und* Simulator, damit die
    # geplante Route und die tatsächlich gefahrene Route nicht auseinanderlaufen.
    # truck_capacity_units = Summe der eingesammelten Füllstände (1 % Füllung
    # ≈ 1 Einheit), ab der der Wagen voll ist und zum Depot zurück muss.
    # Bewusst so gewählt, dass die Grenze bei vollem Demo-Bestand (~35 Tonnen)
    # sichtbar greift und die Route kürzer wird.
    truck_capacity_units: float = 1500.0
    # Nur Tonnen ab diesem Füllstand lohnen die Anfahrt / werden gesammelt.
    collect_fill_threshold: int = 60

    class Config:
        env_file = ".env"


settings = Settings()
