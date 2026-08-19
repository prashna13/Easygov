"""
Unit tests for the haversine distance calculation and the nearby-office
filtering/sorting logic used by GET /api/v1/offices/nearby.
"""

import pytest

from app.geo import EARTH_RADIUS_KM, find_nearby_offices, haversine_km


# ── HAVERSINE ────────────────────────────────────────────────────────────────

def test_zero_distance():
    assert haversine_km(27.7, 85.32, 27.7, 85.32) == 0.0


def test_latitude_minute_scale():
    # 1 degree of latitude is ~111.195 km at the equator.
    assert haversine_km(0, 0, 1, 0) == pytest.approx(111.195, abs=0.5)


def test_kathmandu_to_lalitpur():
    # Kathmandu DAO (Tripureshwor) to Lalitpur DAO (Pulchowk) is a few km.
    d = haversine_km(27.6955, 85.3186, 27.6741, 85.3194)
    assert d == pytest.approx(2.4, abs=0.5)


def test_kathmandu_to_pokhara():
    # Straight-line Kathmandu -> Pokhara is ~140-150 km (road is much further,
    # ~200 km). The exact value depends on the chosen coordinates.
    d = haversine_km(27.6955, 85.3186, 28.2096, 83.9856)
    assert 135 < d < 155


def test_symmetry():
    a = (27.6955, 85.3186)
    b = (28.2096, 83.9856)
    assert haversine_km(*a, *b) == pytest.approx(haversine_km(*b, *a))


def test_london_to_new_york():
    # Well-known reference: ~5570 km great-circle.
    d = haversine_km(51.5074, -0.1278, 40.7128, -74.0060)
    assert d == pytest.approx(5570, abs=30)


def test_radius_constant_sane():
    assert 6300 < EARTH_RADIUS_KM < 6400


# ── FILTERING / SORTING ──────────────────────────────────────────────────────

KATHMANDU_DAO = {
    "id": 1,
    "name": "Kathmandu District Administration Office",
    "service_tags": "citizenship,identity",
    "latitude": 27.6955,
    "longitude": 85.3186,
}
LALITPUR_DAO = {
    "id": 2,
    "name": "Lalitpur District Administration Office",
    "service_tags": "citizenship,identity",
    "latitude": 27.6741,
    "longitude": 85.3194,
}
TRANSPORT_OFFICE = {
    "id": 3,
    "name": "Department of Transport Management",
    "service_tags": "driving_license,transport",
    "latitude": 27.6656,
    "longitude": 85.3184,
}
NEPALGUNJ_DAO = {
    "id": 4,
    "name": "Banke District Administration Office",
    "service_tags": "citizenship,identity",
    "latitude": 28.0585,
    "longitude": 81.6120,
}
NOMAD_OFFICE = {
    "id": 5,
    "name": "Missing Coordinates Office",
    "service_tags": "citizenship,identity",
    "latitude": None,
    "longitude": None,
}


def test_filters_by_service_type():
    offices = [KATHMANDU_DAO, TRANSPORT_OFFICE]
    result = find_nearby_offices(offices, "citizenship", 27.7, 85.32, 100)
    assert [o["name"] for o in result] == ["Kathmandu District Administration Office"]


def test_service_type_is_case_insensitive():
    offices = [KATHMANDU_DAO]
    result = find_nearby_offices(offices, "CitiZENSHIP", 27.7, 85.32, 100)
    assert len(result) == 1


def test_radius_filters_out_far_offices():
    offices = [KATHMANDU_DAO, NEPALGUNJ_DAO]
    # 1 km radius around KTM DAO keeps only KTM DAO; Nepalgunj is ~380 km away.
    result = find_nearby_offices(offices, "citizenship", 27.6955, 85.3186, 1)
    assert len(result) == 1
    assert result[0]["name"] == "Kathmandu District Administration Office"


def test_larger_radius_includes_more():
    offices = [KATHMANDU_DAO, LALITPUR_DAO]
    tight = find_nearby_offices(offices, "citizenship", 27.6955, 85.3186, 1)
    wide = find_nearby_offices(offices, "citizenship", 27.6955, 85.3186, 20)
    assert len(tight) == 1
    assert len(wide) == 2


def test_sorted_nearest_first():
    offices = [LALITPUR_DAO, NEPALGUNJ_DAO, KATHMANDU_DAO]
    result = find_nearby_offices(offices, "citizenship", 27.6955, 85.3186, 500)
    assert result[0]["name"] == "Kathmandu District Administration Office"
    assert result[-1]["name"] == "Banke District Administration Office"
    distances = [o["distance_km"] for o in result]
    assert distances == sorted(distances)


def test_distance_km_rounded_and_present():
    result = find_nearby_offices([KATHMANDU_DAO], "citizenship", 27.7, 85.32, 100)
    assert "distance_km" in result[0]
    assert isinstance(result[0]["distance_km"], float)


def test_skips_missing_coordinates():
    offices = [KATHMANDU_DAO, NOMAD_OFFICE]
    result = find_nearby_offices(offices, "citizenship", 27.7, 85.32, 100)
    assert len(result) == 1
    assert result[0]["id"] == 1


def test_empty_result_when_nothing_matches():
    assert find_nearby_offices([KATHMANDU_DAO], "nid", 27.7, 85.32, 100) == []


def test_empty_result_when_nothing_in_radius():
    offices = [KATHMANDU_DAO, LALITPUR_DAO]
    # Query point far away (Lumbini) with a tiny radius.
    result = find_nearby_offices(offices, "citizenship", 27.5055, 83.4543, 1)
    assert result == []


def test_blank_service_type_returns_empty():
    assert find_nearby_offices([KATHMANDU_DAO], "  ", 27.7, 85.32, 100) == []