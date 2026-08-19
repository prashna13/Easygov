"""
Integration tests for GET /api/v1/offices/nearby.

Uses an isolated in-memory SQLite database (the real db_storage/easygov.db is
never touched) by overriding the `get_db` dependency on a lightweight app
that just mounts the offices router.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.models import Base, GovernmentOffice
from app.offices import router as offices_router


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(offices_router)
    app.dependency_overrides[get_db] = override_get_db

    with testing_session() as db:
        db.add_all(
            [
                GovernmentOffice(
                    name="Kathmandu District Administration Office",
                    office_type="District Administration Office (DAO)",
                    service_tags="citizenship,identity",
                    district="Kathmandu",
                    address="Tripureshwor, Kathmandu",
                    latitude=27.6955,
                    longitude=85.3186,
                    phone="01-4211650",
                    hours="10:00-17:00",
                ),
                GovernmentOffice(
                    name="Lalitpur District Administration Office",
                    office_type="District Administration Office (DAO)",
                    service_tags="citizenship,identity",
                    district="Lalitpur",
                    address="Pulchowk, Lalitpur",
                    latitude=27.6741,
                    longitude=85.3194,
                    phone="01-5522444",
                    hours="10:00-17:00",
                ),
                GovernmentOffice(
                    name="Department of Transport Management",
                    office_type="Department of Transport Management (DOTM)",
                    service_tags="driving_license,transport",
                    district="Lalitpur",
                    address="Ekantakuna, Lalitpur",
                    latitude=27.6656,
                    longitude=85.3184,
                    phone="01-5536013",
                    hours="10:00-17:00",
                ),
                GovernmentOffice(
                    name="Banke District Administration Office",
                    office_type="District Administration Office (DAO)",
                    service_tags="citizenship,identity",
                    district="Banke",
                    address="Nepalgunj, Banke",
                    latitude=28.0585,
                    longitude=81.6120,
                    phone="081-525503",
                    hours="10:00-17:00",
                ),
            ]
        )
        db.commit()

    with TestClient(app) as test_client:
        yield test_client

    Base.metadata.drop_all(bind=engine)


def test_nearby_returns_sorted_filtered(client):
    resp = client.get(
        "/api/v1/offices/nearby",
        params={"service_type": "citizenship", "lat": 27.6955, "lng": 85.3186, "radius": 20},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2  # KTM DAO + LAL DAO (Banke is ~380 km away)
    assert body[0]["name"] == "Kathmandu District Administration Office"
    assert body[1]["name"] == "Lalitpur District Administration Office"
    assert body[0]["distance_km"] < body[1]["distance_km"]
    # service_tags serialized as a list
    assert "citizenship" in body[0]["service_tags"]


def test_nearby_narrow_radius(client):
    resp = client.get(
        "/api/v1/offices/nearby",
        params={"service_type": "citizenship", "lat": 27.6955, "lng": 85.3186, "radius": 1},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_nearby_other_service_type(client):
    resp = client.get(
        "/api/v1/offices/nearby",
        params={"service_type": "driving_license", "lat": 27.7, "lng": 85.32, "radius": 100},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["name"] == "Department of Transport Management"


def test_nearby_empty_results(client):
    resp = client.get(
        "/api/v1/offices/nearby",
        params={"service_type": "passport", "lat": 27.7, "lng": 85.32, "radius": 50},
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_nearby_missing_service_type_is_422(client):
    resp = client.get("/api/v1/offices/nearby", params={"lat": 27.7, "lng": 85.32})
    assert resp.status_code == 422


def test_nearby_invalid_coordinates_are_422(client):
    resp = client.get(
        "/api/v1/offices/nearby",
        params={"service_type": "citizenship", "lat": 95, "lng": 85.32, "radius": 10},
    )
    assert resp.status_code == 422


def test_nearby_zero_radius_is_422(client):
    resp = client.get(
        "/api/v1/offices/nearby",
        params={"service_type": "citizenship", "lat": 27.7, "lng": 85.32, "radius": 0},
    )
    assert resp.status_code == 422


def test_nearby_inactive_office_excluded(client):
    # Add an inactive office very close to the query point.
    app = next(iter(client.app.dependency_overrides.values()))
    engine = None  # placeholder; handled through the fixture's session db below

    # Re-query through the same client — the inactive office is added directly
    # to the shared in-memory db via the override get_db.
    insert_inactive(client)
    resp = client.get(
        "/api/v1/offices/nearby",
        params={"service_type": "passport", "lat": 27.6955, "lng": 85.3186, "radius": 20},
    )
    assert resp.status_code == 200
    names = [o["name"] for o in resp.json()]
    assert "Inactive Passport Office" not in names


def insert_inactive(client):
    """Add an inactive office row through the shared in-memory session."""
    override = client.app.dependency_overrides[get_db]
    gen = override()
    db = next(gen)
    try:
        office = GovernmentOffice(
            name="Inactive Passport Office",
            office_type="Department of Passports",
            service_tags="passport,identity",
            district="Kathmandu",
            address="Tripureshwor, Kathmandu",
            latitude=27.6955,
            longitude=85.3186,
            phone="01-0000000",
            hours="10:00-15:00",
            is_active=False,
        )
        db.add(office)
        db.commit()
    finally:
        gen.close()