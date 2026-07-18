"""Statistics routes — query visit analytics."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    OverviewResponse,
    DailyResponse,
    DayCount,
    BrowsersResponse,
    NameCount,
    OsResponse,
    PagesResponse,
    PageCount,
    ReferrersResponse,
    ReferrerCount,
    DevicesResponse,
    DeviceCount,
)
from app.services import stats_service

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/overview", response_model=OverviewResponse)
def overview(db: Session = Depends(get_db)):
    """Return overall visit statistics."""
    return stats_service.get_overview(db)


@router.get("/daily", response_model=DailyResponse)
def daily(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Return daily visit counts for the last N days."""
    data = stats_service.get_daily(db, days=days)
    return DailyResponse(days=[DayCount(**d) for d in data])


@router.get("/browsers", response_model=BrowsersResponse)
def browsers(db: Session = Depends(get_db)):
    """Return browser distribution with percentages."""
    data = stats_service.get_browsers(db)
    return BrowsersResponse(browsers=[NameCount(**d) for d in data])


@router.get("/os", response_model=OsResponse)
def operating_system(db: Session = Depends(get_db)):
    """Return OS distribution with percentages."""
    data = stats_service.get_os(db)
    return OsResponse(os=[NameCount(**d) for d in data])


@router.get("/pages", response_model=PagesResponse)
def pages(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Return top pages by visit count."""
    data = stats_service.get_pages(db, limit=limit)
    return PagesResponse(pages=[PageCount(**d) for d in data])


@router.get("/referrers", response_model=ReferrersResponse)
def referrers(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Return top referrer sources."""
    data = stats_service.get_referrers(db, limit=limit)
    return ReferrersResponse(referrers=[ReferrerCount(**d) for d in data])


@router.get("/devices", response_model=DevicesResponse)
def devices(db: Session = Depends(get_db)):
    """Return device type distribution with percentages."""
    data = stats_service.get_devices(db)
    return DevicesResponse(devices=[DeviceCount(**d) for d in data])
