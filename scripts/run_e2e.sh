#!/usr/bin/env bash
# run_e2e.sh — full local E2E test orchestrator
#
# Usage:
#   bash scripts/run_e2e.sh              # run all e2e tests
#   bash scripts/run_e2e.sh -k browser  # run only browser tests
#   bash scripts/run_e2e.sh -k api      # run only API tests
#
# Extra args are passed through to pytest.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Load .env so service processes inherit the right config
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

PORTAL_URL="${PORTAL_URL:-http://localhost:8030}"
VERIFY_URL="${VERIFY_URL:-http://localhost:8040}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"

PIDS=()
FRONTEND_PID=""

cleanup() {
  echo ""
  echo "==> Cleaning up background processes..."
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  [[ -n "$FRONTEND_PID" ]] && kill "$FRONTEND_PID" 2>/dev/null || true
  echo "==> Done."
}
trap cleanup EXIT

# ---------------------------------------------------------------------------
# 1. Prerequisites
# ---------------------------------------------------------------------------
echo "==> Checking prerequisites..."

for cmd in python docker npm node; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "ERROR: '$cmd' not found. See build.md."; exit 1; }
done

python -c "import playwright" 2>/dev/null || {
  echo "==> Installing e2e dependencies..."
  pip install -r requirements-e2e.txt
  playwright install chromium
}

# ---------------------------------------------------------------------------
# 2. Infrastructure (Postgres + Redis)
# ---------------------------------------------------------------------------
echo "==> Starting Docker infrastructure..."
docker compose up -d postgres redis

echo "==> Waiting for Postgres to be healthy..."
for i in $(seq 1 30); do
  if docker compose exec -T postgres pg_isready -U dstn -q 2>/dev/null; then
    break
  fi
  [[ $i -eq 30 ]] && { echo "ERROR: Postgres did not become healthy."; exit 1; }
  sleep 1
done

# ---------------------------------------------------------------------------
# 3. Database migrations
# ---------------------------------------------------------------------------
echo "==> Running Alembic migrations..."
alembic upgrade head

# ---------------------------------------------------------------------------
# 4. Python services
# ---------------------------------------------------------------------------
_wait_up() {
  local url="$1/health"
  local label="$2"
  for i in $(seq 1 30); do
    if curl -sf "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  echo "ERROR: $label did not start at $url"
  exit 1
}

if ! curl -sf "${PORTAL_URL}/health" >/dev/null 2>&1; then
  echo "==> Starting portal backend..."
  PYTHONPATH="$REPO_ROOT:$REPO_ROOT/services/portal" \
    python -m uvicorn portal.main:app --port 8030 \
    >"$REPO_ROOT/.e2e-portal.log" 2>&1 &
  PIDS+=($!)
  _wait_up "$PORTAL_URL" "Portal"
else
  echo "==> Portal already running at $PORTAL_URL"
fi

if ! curl -sf "${VERIFY_URL}/health" >/dev/null 2>&1; then
  echo "==> Starting verification API..."
  PYTHONPATH="$REPO_ROOT:$REPO_ROOT/services/verification" \
    python -m uvicorn verification.main:app --port 8040 \
    >"$REPO_ROOT/.e2e-verification.log" 2>&1 &
  PIDS+=($!)
  _wait_up "$VERIFY_URL" "Verification API"
else
  echo "==> Verification API already running at $VERIFY_URL"
fi

# ---------------------------------------------------------------------------
# 5. Widget bundle (build if missing)
# ---------------------------------------------------------------------------
if [[ ! -f services/verification/static/widget.js ]]; then
  echo "==> Building verifier widget..."
  (cd frontend/widget && npm install --silent && node build.js)
fi

# ---------------------------------------------------------------------------
# 6. Frontend dev server
# ---------------------------------------------------------------------------
if ! curl -sf "${FRONTEND_URL}" >/dev/null 2>&1; then
  echo "==> Starting React frontend (npm run dev)..."
  (cd frontend/portal && npm install --silent) >/dev/null 2>&1
  (cd frontend/portal && npm run dev -- --port 3000) \
    >"$REPO_ROOT/.e2e-frontend.log" 2>&1 &
  FRONTEND_PID=$!

  echo "==> Waiting for frontend..."
  for i in $(seq 1 45); do
    if curl -sf "${FRONTEND_URL}" >/dev/null 2>&1; then
      break
    fi
    [[ $i -eq 45 ]] && { echo "ERROR: Frontend did not start. Check .e2e-frontend.log"; exit 1; }
    sleep 1
  done
else
  echo "==> Frontend already running at $FRONTEND_URL"
fi

# ---------------------------------------------------------------------------
# 7. Run tests
# ---------------------------------------------------------------------------
echo ""
echo "==> All services up. Running e2e tests..."
echo ""

pytest tests/e2e/ -v "$@"
