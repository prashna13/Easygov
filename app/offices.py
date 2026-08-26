"""
offices.py
----------
FastAPI router for the curated government-office catalog.

The "Find Nearest Office" feature searches a static, seeded set of real
Nepali government offices (District Administration Offices, passport and NID
enrollment centers, transport management offices, ...). It does NOT perform
a live Google Places search.

Endpoint:
    GET /api/v1/offices/nearby?service_type=citizenship&lat=27.70&lng=85.32&radius=20
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.geo import find_nearby_offices
from app.models import GovernmentOffice as DBGovernmentOffice
from app.schemas import GovernmentOfficeOut

router = APIRouter(prefix="/api/v1/offices", tags=["offices"])


def _office_out(office: DBGovernmentOffice, distance_km: Optional[float] = None) -> GovernmentOfficeOut:
    """Convert a GovernmentOffice row to the API schema (tags string -> list)."""
    tags = [t.strip() for t in (office.service_tags or "").split(",") if t.strip()]
    return GovernmentOfficeOut(
        id=office.id,
        name=office.name,
        office_type=office.office_type,
        service_tags=tags,
        district=office.district,
        address=office.address,
        latitude=office.latitude,
        longitude=office.longitude,
        phone=office.phone,
        hours=office.hours,
        distance_km=distance_km,
        note=office.note,
    )


@router.get("/nearby", response_model=List[GovernmentOfficeOut])
def nearby_offices(
    service_type: str = Query(..., min_length=1, description="Office tag, e.g. citizenship, nid, passport, driving_license"),
    lat: float = Query(..., ge=-90, le=90, description="Query latitude (WGS84)"),
    lng: float = Query(..., ge=-180, le=180, description="Query longitude (WGS84)"),
    radius: float = Query(10.0, gt=0, le=100, description="Search radius in kilometres (default 10, max 100)"),
    db: Session = Depends(get_db),
):
    """Return offices serving `service_type` within `radius` km of (lat, lng),
    sorted nearest-first, each annotated with its haversine `distance_km`."""
    offices = (
        db.query(DBGovernmentOffice)
        .filter(DBGovernmentOffice.is_active == True)
        .all()
    )

    nearby = find_nearby_offices(
        [office.__dict__ for office in offices],
        service_type,
        lat,
        lng,
        radius,
    )

    # Re-map the row dicts back onto the schema. Use the original rows so the
    # response never leaks internal SQLAlchemy state.
    office_by_id = {office.id: office for office in offices}
    results: List[GovernmentOfficeOut] = []
    for item in nearby:
        office = office_by_id.get(item.get("id"))
        if office is None:
            continue
        results.append(_office_out(office, distance_km=item.get("distance_km")))
    return results