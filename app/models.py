"""SQLAlchemy ORM models."""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime, Index

from app.database import Base


class User(Base):
    """OAuth-authenticated user."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sub = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True, default="")
    email = Column(String(255), nullable=True, default="")
    picture = Column(String(512), nullable=True, default="")
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self):
        return f"<User sub={self.sub!r} username={self.username!r}>"


class Visit(Base):
    """A single page visit recorded by the tracker."""

    __tablename__ = "visits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    visitor_ip = Column(String(45), nullable=False)
    page_url = Column(String(2048), nullable=False)
    referrer = Column(Text, nullable=True)
    screen_resolution = Column(String(20), nullable=True)
    language = Column(String(20), nullable=True)
    title = Column(String(512), nullable=True)

    # Parsed from User-Agent
    browser_name = Column(String(50), nullable=True)
    browser_version = Column(String(50), nullable=True)
    os_name = Column(String(50), nullable=True)
    os_version = Column(String(50), nullable=True)
    device_type = Column(String(20), nullable=True)

    # Raw
    user_agent = Column(Text, nullable=True)

    # Timestamp
    visited_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Indexes for common queries
    __table_args__ = (
        Index("ix_visits_visitor_ip", visitor_ip),
        Index("ix_visits_page_url", page_url),
        Index("ix_visits_visited_at", visited_at),
    )

    def __repr__(self):
        return f"<Visit id={self.id} page={self.page_url!r} ip={self.visitor_ip}>"
