# 🐜 Ant Cave Analytics

A lightweight, self-hosted website visitor tracking and analytics system built with **FastAPI + SQLite**.

## Features

- 📊 **Track page visits** — browser info, screen resolution, referrer, language, and more
- 🕵️ **User-Agent parsing** — extracts browser, OS, and device type (no external libs)
- 📈 **Dashboard** — dark-themed Chart.js dashboard with auto-refresh
- 📦 **Embeddable JS tracker** — drop-in `<script>` tag
- 🗄️ **SQLite storage** — zero configuration, perfect for personal/small sites
- 🚀 **Simple deployment** — systemd service file included

## Quick Start

```bash
# 1. Bootstrap environment
bash scripts/setup.sh

# 2. Start server (development)
venv/bin/python run.py --reload

# 3. Test the API
curl http://localhost:8000/api/stats/overview
```

The server runs on **http://localhost:8000** by default.

## API Endpoints

### Tracking
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/track` | Record a single page visit |
| POST | `/api/track/batch` | Record multiple visits at once |

### Statistics
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/stats/overview` | Total visits, unique IPs, today, active now |
| GET | `/api/stats/daily?days=30` | Daily visit trend |
| GET | `/api/stats/browsers` | Browser distribution |
| GET | `/api/stats/os` | OS distribution |
| GET | `/api/stats/pages?limit=10` | Top pages |
| GET | `/api/stats/referrers?limit=10` | Top referrers |
| GET | `/api/stats/devices` | Device type breakdown |

### Frontend
| Method | Path | Description |
|--------|------|-------------|
| GET | `/dashboard` | Analytics dashboard HTML |
| GET | `/tracker.js` | Embeddable tracking script |

## Usage

### 1. Add the tracker to your website

```html
<script src="https://your-server.com/tracker.js" async></script>
```

Or configure a custom endpoint:
```html
<script>
  window._antTrackEndpoint = "https://your-server.com/api/track";
</script>
<script src="https://your-server.com/tracker.js" async></script>
```

### 2. View the analytics dashboard

Open `https://your-server.com/dashboard` in your browser.

### 3. Consume the API directly

```bash
# Track a visit
curl -X POST http://localhost:8000/api/track \
  -H "Content-Type: application/json" \
  -d '{"page_url": "https://example.com/page1"}'

# Get overview stats
curl http://localhost:8000/api/stats/overview
```

## Production Deployment

```bash
sudo cp systemd/ant-cave-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ant-cave-backend
```

### Reverse Proxy (Caddy example)

```caddyfile
analytics.example.com {
    reverse_proxy localhost:8000
}
```

## Configuration

Set these environment variables to customize:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./data/analytics.db` | SQLite database path |
| `CORS_ORIGINS` | `*` | Comma-separated allowed CORS origins |
| `ACTIVE_WINDOW_MINUTES` | `30` | Window for "active now" count |
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8000` | Bind port |

## Development

```bash
# Install from scratch
bash scripts/setup.sh

# Run with auto-reload
venv/bin/python run.py --reload

# Run with custom port
venv/bin/python run.py --port 8080
```

## Architecture

```
Visitor Browser
  │
  ├─ <script src=".../tracker.js"> ──→ POST /api/track
  │                                      │
  ▼                                      ▼
Analyzer Dashboard  ◄── GET /api/stats/* ── FastAPI + SQLite
```

- **No external JS build step** — just vanilla JS and CDN-loaded Chart.js
- **No async complexity** — sync SQLAlchemy with SQLite is perfect for this scale
- **Server-side UA parsing** via regex — no extra libraries
- Only **3 Python dependencies**: FastAPI, Uvicorn, SQLAlchemy

## License

MIT
