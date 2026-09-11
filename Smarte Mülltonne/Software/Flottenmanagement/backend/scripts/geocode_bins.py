"""One-shot geocoder for the FH-Viertel bin cluster (50 bins, 4 Cluster).

Queries Nominatim für jede Adresse (strukturiert) und gibt sowohl Logs nach
stderr als auch ein JSON-Blob nach stdout aus.
"""
import json
import sys
import time
import urllib.parse
import urllib.request

# (short_name, street_with_number)
ADDRESSES: list[tuple[str, str]] = [
    # Cluster 1: Westfalenweg
    ("Westfalenweg 1",   "Westfalenweg 1"),
    ("Westfalenweg 2",   "Westfalenweg 2"),
    ("Westfalenweg 3",   "Westfalenweg 3"),
    ("Westfalenweg 4",   "Westfalenweg 4"),
    ("Westfalenweg 5",   "Westfalenweg 5"),
    ("Westfalenweg 6",   "Westfalenweg 6"),
    ("Westfalenweg 7",   "Westfalenweg 7"),
    ("Westfalenweg 8",   "Westfalenweg 8"),
    ("Westfalenweg 9",   "Westfalenweg 9"),
    ("Westfalenweg 10",  "Westfalenweg 10"),
    # Cluster 2: Kasernenweg
    ("Kasernenweg 1",    "Kasernenweg 1"),
    ("Kasernenweg 3",    "Kasernenweg 3"),
    ("Kasernenweg 5",    "Kasernenweg 5"),
    ("Kasernenweg 7",    "Kasernenweg 7"),
    ("Kasernenweg 9",    "Kasernenweg 9"),
    ("Kasernenweg 11",   "Kasernenweg 11"),
    ("Kasernenweg 13",   "Kasernenweg 13"),
    # Cluster 3: Christian-Rohlfs-Straße
    ("Christian-Rohlfs 2",  "Christian-Rohlfs-Straße 2"),
    ("Christian-Rohlfs 4",  "Christian-Rohlfs-Straße 4"),
    ("Christian-Rohlfs 6",  "Christian-Rohlfs-Straße 6"),
    ("Christian-Rohlfs 8",  "Christian-Rohlfs-Straße 8"),
    ("Christian-Rohlfs 10", "Christian-Rohlfs-Straße 10"),
    ("Christian-Rohlfs 12", "Christian-Rohlfs-Straße 12"),
    ("Christian-Rohlfs 14", "Christian-Rohlfs-Straße 14"),
    ("Christian-Rohlfs 16", "Christian-Rohlfs-Straße 16"),
    ("Christian-Rohlfs 18", "Christian-Rohlfs-Straße 18"),
    ("Christian-Rohlfs 20", "Christian-Rohlfs-Straße 20"),
    # Cluster 4: Im Tabaksgang / Elsa-Brandström
    ("Im Tabaksgang 1",  "Im Tabaksgang 1"),
    ("Im Tabaksgang 3",  "Im Tabaksgang 3"),
    ("Im Tabaksgang 5",  "Im Tabaksgang 5"),
    ("Im Tabaksgang 2",  "Im Tabaksgang 2"),
    ("Im Tabaksgang 4",  "Im Tabaksgang 4"),
    ("Elsa-Brandström 1","Elsa-Brandström-Straße 1"),
    ("Elsa-Brandström 3","Elsa-Brandström-Straße 3"),
    ("Elsa-Brandström 5","Elsa-Brandström-Straße 5"),
    ("Elsa-Brandström 7","Elsa-Brandström-Straße 7"),
    # FH Campus echte Tonne
    ("FH Campus",        "Lübecker Ring 2"),
    # Siegener Straße
    ("Siegener Str. 1",  "Siegener Straße 1"),
    ("Siegener Str. 2",  "Siegener Straße 2"),
    ("Siegener Str. 3",  "Siegener Straße 3"),
    ("Siegener Str. 4",  "Siegener Straße 4"),
    ("Siegener Str. 5",  "Siegener Straße 5"),
    ("Siegener Str. 6",  "Siegener Straße 6"),
    ("Siegener Str. 8",  "Siegener Straße 8"),
    ("Siegener Str. 10", "Siegener Straße 10"),
    ("Siegener Str. 12", "Siegener Straße 12"),
    ("Siegener Str. 14", "Siegener Straße 14"),
    ("Siegener Str. 16", "Siegener Straße 16"),
    ("Siegener Str. 18", "Siegener Straße 18"),
    ("Siegener Str. 20", "Siegener Straße 20"),
]

DEPOT = ("Betriebshof Doyenweg", "Doyenweg 21")


def geocode(street: str) -> tuple[float, float] | None:
    params = {
        "format": "json",
        "street": street,
        "city": "Soest",
        "postalcode": "59494",
        "country": "Germany",
        "limit": "1",
    }
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "smart-bin-demo/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.load(r)
    if not data:
        return None
    return float(data[0]["lat"]), float(data[0]["lon"])


def main():
    out = {"bins": [], "depot": None, "missing": []}
    for name, street in ADDRESSES + [DEPOT]:
        try:
            coord = geocode(street)
        except Exception as e:
            coord = None
            print(f"ERROR {street}: {e}", file=sys.stderr)
        entry = {"name": name, "address": f"{street}, 59494 Soest", "coord": coord}
        if (name, street) == DEPOT:
            out["depot"] = entry
        else:
            out["bins"].append(entry)
            if coord is None:
                out["missing"].append(name)
        marker = "OK " if coord else "MISS"
        print(f"{marker}  {name:22s} {street:32s} → {coord}", file=sys.stderr)
        time.sleep(1.1)  # Nominatim rate limit
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
