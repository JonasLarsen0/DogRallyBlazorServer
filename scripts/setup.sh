#!/usr/bin/env bash
# setup.sh — Fresh VM setup for the RejseplanAPI Smart Commuter Dashboard
# Run once after cloning the repository on a new Proxmox VM.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Colour

info()    { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }
die()     { error "$*"; exit 1; }

# ── Dependency checks ─────────────────────────────────────────────────────────
info "Checking dependencies..."

if ! command -v docker &>/dev/null; then
    die "Docker is not installed. Install it from https://docs.docker.com/engine/install/ and re-run this script."
fi

# Support both 'docker compose' (plugin) and 'docker-compose' (standalone)
if docker compose version &>/dev/null 2>&1; then
    COMPOSE="docker compose"
elif command -v docker-compose &>/dev/null; then
    COMPOSE="docker-compose"
else
    die "Docker Compose is not available. Install the Docker Compose plugin and re-run this script."
fi

info "Docker:         $(docker --version)"
info "Docker Compose: $($COMPOSE version)"

# ── Environment file ──────────────────────────────────────────────────────────
cd "$REPO_ROOT"

if [[ -f .env ]]; then
    warn ".env already exists — skipping copy from .env.example."
else
    info "Creating .env from .env.example..."
    cp .env.example .env
    warn "A new .env file has been created."
fi

# Check whether the API key placeholder is still present
if grep -q "your_api_key_here" .env; then
    echo
    warn "REJSEPLANEN_API_KEY is not set."
    echo -e "  Open ${YELLOW}.env${NC} in your editor and replace ${YELLOW}your_api_key_here${NC} with your real key."
    echo
    read -rp "Press Enter once you have saved your API key, or Ctrl-C to abort and edit first... "
    echo
fi

# Final guard — refuse to start if the key is still a placeholder
if grep -q "your_api_key_here" .env; then
    die "REJSEPLANEN_API_KEY is still set to the placeholder value. Edit .env and re-run."
fi

# ── Build and start ───────────────────────────────────────────────────────────
info "Building images and starting services..."
$COMPOSE up -d --build

# ── Status ────────────────────────────────────────────────────────────────────
echo
info "Services are starting. Current status:"
$COMPOSE ps

echo
info "Dashboard will be available at http://$(hostname -I | awk '{print $1}') once all containers are healthy."
info "To tail logs: $COMPOSE logs -f"
info "To stop:      $COMPOSE down"
