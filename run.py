#!/usr/bin/env python3
"""
CLI entry point for the Ant Cave Analytics backend.

Usage:
    python run.py                  # Run with defaults
    python run.py --port 8080      # Custom port
    python run.py --reload         # Auto-reload on code changes
"""

import argparse
import os

import uvicorn

from app.config import HOST, PORT


def main():
    parser = argparse.ArgumentParser(
        description="Ant Cave Analytics — FastAPI visitor tracking backend"
    )
    parser.add_argument(
        "--host",
        default=HOST,
        help=f"Bind address (default: {HOST})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=PORT,
        help=f"Bind port (default: {PORT})",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (default: 1)",
    )
    parser.add_argument(
        "--panel-password",
        default="",
        help="Password for the dashboard GUI (default: no password)",
    )

    args = parser.parse_args()

    if args.panel_password:
        os.environ["PANEL_PASSWORD"] = args.panel_password

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers,
    )


if __name__ == "__main__":
    main()
