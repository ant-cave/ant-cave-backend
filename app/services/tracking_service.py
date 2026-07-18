"""Business logic for recording visits."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Visit
from app.services.user_agent_parser import parse_user_agent


def create_visit(
    db: Session,
    page_url: str,
    visitor_ip: str,
    referrer: str | None = None,
    screen_resolution: str | None = None,
    language: str | None = None,
    title: str | None = None,
    user_agent: str | None = None,
    visit_time: str | None = None,
) -> int:
    """
    Record a single visit and return its ID.

    The User-Agent string is parsed into browser/OS/device fields.
    """
    # Parse User-Agent
    ua_info = parse_user_agent(user_agent)

    # Parse optional visit_time, or use current time
    if visit_time:
        try:
            visited_at = datetime.fromisoformat(visit_time)
        except (ValueError, TypeError):
            visited_at = datetime.now(timezone.utc)
    else:
        visited_at = datetime.now(timezone.utc)

    visit = Visit(
        visitor_ip=visitor_ip,
        page_url=page_url,
        referrer=referrer if referrer else None,
        screen_resolution=screen_resolution,
        language=language,
        title=title,
        user_agent=user_agent,
        browser_name=ua_info["browser_name"],
        browser_version=ua_info["browser_version"],
        os_name=ua_info["os_name"],
        os_version=ua_info["os_version"],
        device_type=ua_info["device_type"],
        visited_at=visited_at,
    )

    db.add(visit)
    db.commit()
    db.refresh(visit)
    return visit.id


def create_visits_batch(
    db: Session,
    events: list[dict],
    default_ip: str,
) -> int:
    """
    Record multiple visits in a single transaction.

    Each event dict should have the same keys as create_visit().
    Returns the number of records created.
    """
    visits = []
    now = datetime.now(timezone.utc)

    for event in events:
        ua_info = parse_user_agent(event.get("user_agent"))

        visit_time_str = event.get("visit_time")
        if visit_time_str:
            try:
                visited_at = datetime.fromisoformat(visit_time_str)
            except (ValueError, TypeError):
                visited_at = now
        else:
            visited_at = now

        visits.append(
            Visit(
                visitor_ip=default_ip,
                page_url=event["page_url"],
                referrer=event.get("referrer") or None,
                screen_resolution=event.get("screen_resolution"),
                language=event.get("language"),
                title=event.get("title"),
                user_agent=event.get("user_agent"),
                browser_name=ua_info["browser_name"],
                browser_version=ua_info["browser_version"],
                os_name=ua_info["os_name"],
                os_version=ua_info["os_version"],
                device_type=ua_info["device_type"],
                visited_at=visited_at,
            )
        )

    db.add_all(visits)
    db.commit()
    return len(visits)
