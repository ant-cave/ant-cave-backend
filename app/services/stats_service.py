"""Business logic for querying visit statistics."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Visit
from app.config import ACTIVE_WINDOW_MINUTES


def get_overview(db: Session) -> dict:
    """Return total_visits, unique_ips, today_visits, active_now."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    active_cutoff = now - timedelta(minutes=ACTIVE_WINDOW_MINUTES)

    total_visits = db.query(func.count(Visit.id)).scalar() or 0
    unique_ips = (
        db.query(func.count(func.distinct(Visit.visitor_ip))).scalar() or 0
    )
    today_visits = (
        db.query(func.count(Visit.id))
        .filter(Visit.visited_at >= today_start)
        .scalar()
        or 0
    )
    active_now = (
        db.query(func.count(func.distinct(Visit.visitor_ip)))
        .filter(Visit.visited_at >= active_cutoff)
        .scalar()
        or 0
    )

    return {
        "total_visits": total_visits,
        "unique_ips": unique_ips,
        "today_visits": today_visits,
        "active_now": active_now,
    }


def get_daily(db: Session, days: int = 30) -> list[dict]:
    """Return visit counts per day for the last N days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        db.query(func.date(Visit.visited_at).label("day"), func.count(Visit.id).label("cnt"))
        .filter(Visit.visited_at >= cutoff)
        .group_by(func.date(Visit.visited_at))
        .order_by("day")
        .all()
    )

    # Build a map {date_str: count}
    counts = {row.day: row.cnt for row in rows}

    # Fill in missing days with zero
    result = []
    for i in range(days):
        d = (cutoff + timedelta(days=i + 1)).strftime("%Y-%m-%d")
        result.append({"date": d, "count": counts.get(d, 0)})

    return result


def _percentages(items: list[tuple[str | None, int]]) -> list[dict]:
    """Convert [(name, count)] to [{name, count, percentage}] with Other bucket."""
    total = sum(c for _, c in items)
    if total == 0:
        return []

    main: list[dict] = []
    other_count = 0
    threshold = total * 0.05  # 5%

    for name, count in items:
        pct = round(count / total * 100, 1)
        if count >= threshold:
            main.append(
                {"name": name or "Unknown", "count": count, "percentage": pct}
            )
        else:
            other_count += count

    if other_count > 0:
        main.append(
            {
                "name": "Other",
                "count": other_count,
                "percentage": round(other_count / total * 100, 1),
            }
        )

    return main


def get_browsers(db: Session) -> list[dict]:
    """Return browser distribution with percentages."""
    rows = (
        db.query(Visit.browser_name, func.count(Visit.id).label("cnt"))
        .group_by(Visit.browser_name)
        .order_by(func.count(Visit.id).desc())
        .all()
    )
    return _percentages([(r.browser_name, r.cnt) for r in rows])


def get_os(db: Session) -> list[dict]:
    """Return OS distribution with percentages."""
    rows = (
        db.query(Visit.os_name, func.count(Visit.id).label("cnt"))
        .group_by(Visit.os_name)
        .order_by(func.count(Visit.id).desc())
        .all()
    )
    return _percentages([(r.os_name, r.cnt) for r in rows])


def get_pages(db: Session, limit: int = 10) -> list[dict]:
    """Return top pages by visit count."""
    rows = (
        db.query(Visit.page_url, func.count(Visit.id).label("cnt"))
        .group_by(Visit.page_url)
        .order_by(func.count(Visit.id).desc())
        .limit(limit)
        .all()
    )
    return [{"url": r.page_url, "count": r.cnt} for r in rows]


def get_referrers(db: Session, limit: int = 10) -> list[dict]:
    """Return top referrer sources."""
    rows = (
        db.query(Visit.referrer, func.count(Visit.id).label("cnt"))
        .group_by(Visit.referrer)
        .order_by(func.count(Visit.id).desc())
        .limit(limit)
        .all()
    )
    result = []
    for r in rows:
        source = r.referrer if r.referrer else "direct"
        # Extract domain from URL referrers for cleaner display
        if source and source.startswith("http"):
            from urllib.parse import urlparse
            try:
                source = urlparse(source).hostname or source
            except Exception:
                pass
        result.append({"source": source, "count": r.cnt})
    return result


def get_devices(db: Session) -> list[dict]:
    """Return device type distribution with percentages."""
    rows = (
        db.query(Visit.device_type, func.count(Visit.id).label("cnt"))
        .group_by(Visit.device_type)
        .order_by(func.count(Visit.id).desc())
        .all()
    )
    result = _percentages([(r.device_type or "Unknown", r.cnt) for r in rows])
    return [{"type": d["name"], "count": d["count"], "percentage": d["percentage"]} for d in result]
