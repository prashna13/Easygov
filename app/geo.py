"""
geo.py
--------
Pure, dependency-free helpers for the "Find Nearest Office" feature.

Kept separate from main.py so the distance/filtering logic can be unit-tested
without booting the full FastAPI app (ChromaDB, embeddings, LLM, ...).
"""

import math

# Mean Earth radius in kilometres (WGS84 approximation).
EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Great-circle distance between two WGS84 coordinates in kilometres.

    Uses the haversine formula, which is accurate to ~0.5% for the kind of
    regional distances the nearby-office feature cares about. Constant
    heading error is negligible within Nepal's districts (far smaller than
    the typical 20–50 km search radius).
    """
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
        * math.sin(d_lng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c


def find_nearby_offices(
    offices,
    service_type: str,
    lat: float,
    lng: float,
    radius_km: float,
):
    """
    Filter a list of office dicts to those serving `service_type` within
    `radius_km` of (lat, lng), and return them sorted by distance (nearest
    first). Each returned dict is augmented with a rounded `distance_km`.

    `offices` may be any iterable of mappings exposing:
        service_tags : comma-separated keys (e.g. "citizenship,identity")
        latitude     : float
        longitude    : float
    Offices with missing/service-tag mismatch/out-of-radius are dropped.
    """
    query_tag = service_type.strip().lower()
    if not query_tag:
        return []

    scored: list[tuple[float, dict]] = []
    for office in offices:
        tags = {
            t.strip().lower()
            for t in (office.get("service_tags") or "").split(",")
            if t.strip()
        }
        if query_tag not in tags:
            continue

        lat2 = office.get("latitude")
        lng2 = office.get("longitude")
        if lat2 is None or lng2 is None:
            continue

        distance = haversine_km(lat, lng, float(lat2), float(lng2))
        if distance > radius_km:
            continue

        enriched = dict(office)
        enriched["distance_km"] = round(distance, 2)
        scored.append((distance, enriched))

    scored.sort(key=lambda pair: pair[0])
    return [item for _, item in scored]