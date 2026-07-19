#!/usr/bin/env python3
"""
Entry point for the Ant Cave Analytics backend.

Usage:
    python run.py                       # Start with CLI
    python run.py --gui                 # Open browser with web login page
    python run.py --gui --port 8080     # Custom port
"""

import argparse
import os
import webbrowser

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
        "--gui",
        action="store_true",
        help="Open browser with the web dashboard",
    )
    parser.add_argument(
        "--panel-password",
        default="",
        help="Password for the web dashboard (default: no password)",
    )

    args = parser.parse_args()

    if args.panel_password:
        os.environ["PANEL_PASSWORD"] = args.panel_password

    if args.gui:
        port = args.port
        print(f"Starting server at http://{args.host}:{port}/dashboard")
        webbrowser.open(f"http://localhost:{port}/dashboard")

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers,
    )


if __name__ == "__main__":
    main()
