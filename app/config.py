"""Application configuration from environment variables."""

import os
from pathlib import Path

# Project root (two levels up from this file)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Database
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{PROJECT_ROOT / 'data' / 'analytics.db'}",
)

# CORS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

# Stats
ACTIVE_WINDOW_MINUTES = int(os.getenv("ACTIVE_WINDOW_MINUTES", "30"))

# Server
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Panel password for web dashboard (empty string = no password required)
PANEL_PASSWORD = os.getenv("PANEL_PASSWORD", "")

# Session secret for dashboard login session
SESSION_SECRET = os.getenv("SESSION_SECRET", "ant-cave-default-secret-change-me")
