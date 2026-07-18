"""Pydantic models for request/response validation."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Request Schemas ──────────────────────────────────────


class TrackEvent(BaseModel):
    """A single tracking event sent from the browser."""

    page_url: str = Field(..., max_length=2048, description="The visited page URL")
    referrer: Optional[str] = Field(None, max_length=2048, description="HTTP referrer")
    screen_resolution: Optional[str] = Field(None, max_length=20)
    language: Optional[str] = Field(None, max_length=20)
    title: Optional[str] = Field(None, max_length=512)
    user_agent: Optional[str] = Field(None, description="Browser User-Agent string")
    visit_time: Optional[str] = Field(
        None, description="ISO 8601 timestamp (server uses current time if omitted)"
    )


class TrackBatch(BaseModel):
    """Multiple tracking events sent in one request."""

    events: list[TrackEvent] = Field(..., min_length=1)


# ── Response Schemas ─────────────────────────────────────


class TrackResponse(BaseModel):
    status: str = "ok"
    visit_id: int


class TrackBatchResponse(BaseModel):
    status: str = "ok"
    recorded: int


class DayCount(BaseModel):
    date: str
    count: int


class DailyResponse(BaseModel):
    days: list[DayCount]


class NameCount(BaseModel):
    name: str
    count: int
    percentage: float


class BrowsersResponse(BaseModel):
    browsers: list[NameCount]


class OsResponse(BaseModel):
    os: list[NameCount]


class PageCount(BaseModel):
    url: str
    count: int


class PagesResponse(BaseModel):
    pages: list[PageCount]


class ReferrerCount(BaseModel):
    source: str
    count: int


class ReferrersResponse(BaseModel):
    referrers: list[ReferrerCount]


class DeviceCount(BaseModel):
    type: str
    count: int
    percentage: float


class DevicesResponse(BaseModel):
    devices: list[DeviceCount]


class OverviewResponse(BaseModel):
    total_visits: int
    unique_ips: int
    today_visits: int
    active_now: int
