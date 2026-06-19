from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # SQLite only
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from models.bin import Bin
    from models.route import Route
    from models.event import SecurityEvent
    from models.command import Command

    Base.metadata.create_all(bind=engine)
    _seed(SessionLocal())


def _seed(db):
    from models.bin import Bin

    if db.query(Bin).count() > 0:
        db.close()
        return

    # 35 Tonnen, kompakter Cluster im FH-Viertel (Soester Süden).
    # Geocodiert via Nominatim (siehe scripts/geocode_bins.py).
    # Bei Westfalenweg-Adressen ohne Hausnummern-Treffer in OSM: deterministischer
    # ±15m-Jitter, damit Marker auf der Karte nicht stacken.
    # Fill/Battery-Verteilung deterministisch (random.seed(42)) für reproduzierbare Demos.
    soest_bins = [
        # Cluster 1: Westfalenweg
        Bin(id=1,  name='Westfalenweg 1',     address='Westfalenweg 1, 59494 Soest',           lat=51.557999, lng=8.112165, fill_level=29, battery=77, solar_output_w=9.8,  is_charging=True,  status='idle', locked=False),
        Bin(id=2,  name='Westfalenweg 2',     address='Westfalenweg 2, 59494 Soest',           lat=51.559407, lng=8.111629, fill_level=62, battery=74, solar_output_w=5.8,  is_charging=True,  status='idle', locked=False),
        Bin(id=3,  name='Westfalenweg 3',     address='Westfalenweg 3, 59494 Soest',           lat=51.558084, lng=8.112156, fill_level=81, battery=83, solar_output_w=11.2, is_charging=True,  status='idle', locked=False),
        Bin(id=4,  name='Westfalenweg 4',     address='Westfalenweg 4, 59494 Soest',           lat=51.559111, lng=8.111598, fill_level=40, battery=80, solar_output_w=10.3, is_charging=True,  status='idle', locked=False),
        Bin(id=5,  name='Westfalenweg 5',     address='Westfalenweg 5, 59494 Soest',           lat=51.558068, lng=8.112228, fill_level=71, battery=74, solar_output_w=10.4, is_charging=True,  status='idle', locked=False),
        Bin(id=6,  name='Westfalenweg 6',     address='Westfalenweg 6, 59494 Soest',           lat=51.558785, lng=8.111668, fill_level=23, battery=95, solar_output_w=7.4,  is_charging=True,  status='idle', locked=False),
        Bin(id=7,  name='Westfalenweg 7',     address='Westfalenweg 7, 59494 Soest',           lat=51.558127, lng=8.112379, fill_level=47, battery=77, solar_output_w=7.1,  is_charging=True,  status='idle', locked=False),
        Bin(id=8,  name='Westfalenweg 8',     address='Westfalenweg 8, 59494 Soest',           lat=51.557971, lng=8.112138, fill_level=76, battery=22, solar_output_w=0.0,  is_charging=False, status='idle', locked=False),
        Bin(id=9,  name='Westfalenweg 9',     address='Westfalenweg 9, 59494 Soest',           lat=51.557753, lng=8.112537, fill_level=88, battery=75, solar_output_w=6.1,  is_charging=True,  status='idle', locked=False),
        Bin(id=10, name='Westfalenweg 10',    address='Westfalenweg 10, 59494 Soest',          lat=51.558055, lng=8.112165, fill_level=80, battery=70, solar_output_w=5.0,  is_charging=True,  status='idle', locked=False),
        # Cluster 2: Kasernenweg
        Bin(id=11, name='Kasernenweg 1',      address='Kasernenweg 1, 59494 Soest',            lat=51.562384, lng=8.111828, fill_level=32, battery=63, solar_output_w=10.1, is_charging=True,  status='idle', locked=False),
        Bin(id=12, name='Kasernenweg 3',      address='Kasernenweg 3, 59494 Soest',            lat=51.562506, lng=8.112153, fill_level=42, battery=77, solar_output_w=10.0, is_charging=True,  status='idle', locked=False),
        Bin(id=13, name='Kasernenweg 5',      address='Kasernenweg 5, 59494 Soest',            lat=51.562376, lng=8.112305, fill_level=40, battery=85, solar_output_w=11.8, is_charging=True,  status='idle', locked=False),
        Bin(id=14, name='Kasernenweg 7',      address='Kasernenweg 7, 59494 Soest',            lat=51.562706, lng=8.112668, fill_level=37, battery=64, solar_output_w=10.3, is_charging=True,  status='idle', locked=False),
        Bin(id=15, name='Kasernenweg 9',      address='Kasernenweg 9, 59494 Soest',            lat=51.562914, lng=8.11312,  fill_level=41, battery=62, solar_output_w=8.6,  is_charging=True,  status='idle', locked=False),
        Bin(id=16, name='Kasernenweg 11',     address='Kasernenweg 11, 59494 Soest',           lat=51.563126, lng=8.113625, fill_level=59, battery=66, solar_output_w=5.7,  is_charging=True,  status='idle', locked=False),
        Bin(id=17, name='Kasernenweg 13',     address='Kasernenweg 13, 59494 Soest',           lat=51.562498, lng=8.11236,  fill_level=79, battery=84, solar_output_w=9.4,  is_charging=True,  status='idle', locked=False),
        # Cluster 3: Elsa-Brandström-Straße
        Bin(id=18, name='Elsa-Brandström 1',  address='Elsa-Brandström-Straße 1, 59494 Soest', lat=51.560127, lng=8.118556, fill_level=86, battery=73, solar_output_w=10.9, is_charging=True,  status='idle', locked=False),
        Bin(id=19, name='Elsa-Brandström 3',  address='Elsa-Brandström-Straße 3, 59494 Soest', lat=51.56007,  lng=8.118314, fill_level=28, battery=20, solar_output_w=0.0,  is_charging=False, status='idle', locked=False),
        Bin(id=20, name='Elsa-Brandström 5',  address='Elsa-Brandström-Straße 5, 59494 Soest', lat=51.560012, lng=8.118109, fill_level=46, battery=89, solar_output_w=8.6,  is_charging=True,  status='idle', locked=False),
        Bin(id=21, name='Elsa-Brandström 7',  address='Elsa-Brandström-Straße 7, 59494 Soest', lat=51.55992,  lng=8.11781,  fill_level=22, battery=83, solar_output_w=6.4,  is_charging=True,  status='idle', locked=False),
        # FH Hauptcampus (echte Tonne)
        Bin(id=22, name='FH Campus',          address='Lübecker Ring 2, 59494 Soest',          lat=51.560548, lng=8.114326, fill_level=84, battery=64, solar_output_w=7.6,  is_charging=True,  status='idle', locked=False),
        # Cluster 4: Siegener Straße
        Bin(id=23, name='Siegener Str. 1',    address='Siegener Straße 1, 59494 Soest',        lat=51.558303, lng=8.114152, fill_level=46, battery=70, solar_output_w=6.1,  is_charging=True,  status='idle', locked=False),
        Bin(id=24, name='Siegener Str. 2',    address='Siegener Straße 2, 59494 Soest',        lat=51.558695, lng=8.113988, fill_level=78, battery=80, solar_output_w=11.7, is_charging=True,  status='idle', locked=False),
        Bin(id=25, name='Siegener Str. 3',    address='Siegener Straße 3, 59494 Soest',        lat=51.558319, lng=8.113952, fill_level=85, battery=94, solar_output_w=11.5, is_charging=True,  status='idle', locked=False),
        Bin(id=26, name='Siegener Str. 4',    address='Siegener Straße 4, 59494 Soest',        lat=51.558574, lng=8.113554, fill_level=89, battery=77, solar_output_w=11.4, is_charging=True,  status='idle', locked=False),
        Bin(id=27, name='Siegener Str. 5',    address='Siegener Straße 5, 59494 Soest',        lat=51.558297, lng=8.113618, fill_level=33, battery=80, solar_output_w=9.2,  is_charging=True,  status='idle', locked=False),
        Bin(id=28, name='Siegener Str. 6',    address='Siegener Straße 6, 59494 Soest',        lat=51.558659, lng=8.1135,   fill_level=57, battery=91, solar_output_w=8.4,  is_charging=True,  status='idle', locked=False),
        Bin(id=29, name='Siegener Str. 8',    address='Siegener Straße 8, 59494 Soest',        lat=51.558496, lng=8.113192, fill_level=72, battery=73, solar_output_w=5.8,  is_charging=True,  status='idle', locked=False),
        Bin(id=30, name='Siegener Str. 10',   address='Siegener Straße 10, 59494 Soest',       lat=51.558583, lng=8.113148, fill_level=88, battery=84, solar_output_w=7.5,  is_charging=True,  status='idle', locked=False),
        Bin(id=31, name='Siegener Str. 12',   address='Siegener Straße 12, 59494 Soest',       lat=51.558402, lng=8.112785, fill_level=71, battery=74, solar_output_w=11.9, is_charging=True,  status='idle', locked=False),
        Bin(id=32, name='Siegener Str. 14',   address='Siegener Straße 14, 59494 Soest',       lat=51.558495, lng=8.112709, fill_level=56, battery=70, solar_output_w=10.6, is_charging=True,  status='idle', locked=False),
        Bin(id=33, name='Siegener Str. 16',   address='Siegener Straße 16, 59494 Soest',       lat=51.558283, lng=8.112445, fill_level=60, battery=82, solar_output_w=6.7,  is_charging=True,  status='idle', locked=False),
        Bin(id=34, name='Siegener Str. 18',   address='Siegener Straße 18, 59494 Soest',       lat=51.558274, lng=8.112385, fill_level=81, battery=89, solar_output_w=6.7,  is_charging=True,  status='idle', locked=False),
        Bin(id=35, name='Siegener Str. 20',   address='Siegener Straße 20, 59494 Soest',       lat=51.55819,  lng=8.112545, fill_level=95, battery=73, solar_output_w=9.0,  is_charging=True,  status='idle', locked=False),
    ]
    db.add_all(soest_bins)
    db.commit()
    db.close()
