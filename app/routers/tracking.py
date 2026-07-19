"""Tracking routes — receive visit data from browsers."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_client_ip
from app.schemas import TrackEvent, TrackBatch, TrackResponse, TrackBatchResponse
from app.services import tracking_service

router = APIRouter(prefix="/api", tags=["tracking"])


@router.post("/track", response_model=TrackResponse, status_code=201)
def track_visit(
    event: TrackEvent,
    request: Request,
    db: Session = Depends(get_db),
):
    """Record a single page visit."""
    # Use User-Agent from header if not provided in body
    ua = event.user_agent or request.headers.get("User-Agent")

    visit_id = tracking_service.create_visit(
        db=db,
        page_url=event.page_url,
        visitor_ip=get_client_ip(request),
        referrer=event.referrer,
        screen_resolution=event.screen_resolution,
        language=event.language,
        title=event.title,
        user_agent=ua,
        visit_time=event.visit_time,
    )
    return TrackResponse(status="ok", visit_id=visit_id)


@router.post("/track/batch", response_model=TrackBatchResponse, status_code=201)
def track_batch(
    batch: TrackBatch,
    request: Request,
    db: Session = Depends(get_db),
):
    """Record multiple page visits in one request."""
    ip = get_client_ip(request)

    # Enrich each event with User-Agent from header if missing
    events_data = []
    for event in batch.events:
        ua = event.user_agent or request.headers.get("User-Agent")
        events_data.append({**event.model_dump(), "user_agent": ua})

    recorded = tracking_service.create_visits_batch(db, events_data, ip)
    return TrackBatchResponse(status="ok", recorded=recorded)
