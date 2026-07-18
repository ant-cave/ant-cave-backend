#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# One-shot bootstrap: install pip, create venv, install deps
# ──────────────────────────────────────────────────────────────
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "==> Installing pip and python3.13-venv..."
sudo apt update
sudo apt install -y python3-pip python3.13-venv

echo "==> Creating virtual environment..."
python3.13 -m venv venv
source venv/bin/activate

echo "==> Upgrading pip..."
pip install --upgrade pip

echo "==> Installing Python dependencies..."
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the server in development mode:"
echo "    cd $PROJECT_DIR"
echo "    venv/bin/python run.py --reload"
echo ""
echo "To start with systemd:"
echo "    sudo cp systemd/ant-cave-backend.service /etc/systemd/system/"
echo "    sudo systemctl daemon-reload"
echo "    sudo systemctl enable --now ant-cave-backend"
