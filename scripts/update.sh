#!/usr/bin/env bash
# update.sh — Pull latest code and rebuild changed services in-place.
# Running containers that have not changed will not be restarted.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ── Colour helpers ────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC}  $*"; }

# ── Resolve compose command ───────────────────────────────────────────────────
if docker compose version &>/dev/null 2>&1; then
    COMPOSE="docker compose"
elif command -v docker-compose &>/dev/null; then
    COMPOSE="docker-compose"
else
    echo "[ERROR] Docker Compose is not available." >&2
    exit 1
fi

cd "$REPO_ROOT"

# ── Pull latest changes ───────────────────────────────────────────────────────
info "Pulling latest changes from git..."
git pull

# ── Rebuild and restart only services with changed images ─────────────────────
info "Rebuilding images and restarting updated services..."
$COMPOSE up -d --build --no-deps

# ── Status ────────────────────────────────────────────────────────────────────
echo
info "Update complete. Current status:"
$COMPOSE ps
