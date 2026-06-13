"""
E2E test fixtures.

Services (portal, verification) are started automatically if not already running.
The Playwright page fixture attaches a CDP WebAuthn virtual authenticator so
passkey flows run headlessly without a real biometric device.

Run with:
    pytest tests/e2e/ --browser chromium -v
or via the orchestration script:
    bash scripts/run_e2e.sh
"""
import os
import secrets
import subprocess
import time
from pathlib import Path

import httpx
import pytest
from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[2]
PORTAL_URL = os.getenv("PORTAL_URL", "http://localhost:8030")
VERIFY_URL = os.getenv("VERIFY_URL", "http://localhost:8040")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
ADMIN_KEY = os.getenv("ADMIN_API_KEY", "change-admin-key")


# ---------------------------------------------------------------------------
# Service management
# ---------------------------------------------------------------------------

def _health(url: str) -> bool:
    try:
        return httpx.get(f"{url}/health", timeout=2).status_code == 200
    except Exception:
        return False


def _wait_up(url: str, timeout: int = 30) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _health(url):
            return True
        time.sleep(0.5)
    return False


def _service_env(service_subdir: str) -> dict:
    """Build env with PYTHONPATH covering repo root + the service directory."""
    service_path = str(REPO_ROOT / service_subdir)
    existing = os.environ.get("PYTHONPATH", "")
    pythonpath = ":".join(filter(None, [str(REPO_ROOT), service_path, existing]))
    return {**os.environ, "PYTHONPATH": pythonpath}


@pytest.fixture(scope="session")
def live_services():
    """Ensure portal and verification API are up; start them if needed."""
    procs = []

    if not _health(PORTAL_URL):
        p = subprocess.Popen(
            ["python", "-m", "uvicorn", "portal.main:app", "--port", "8030"],
            cwd=str(REPO_ROOT),
            env=_service_env("services/portal"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        procs.append(p)

    if not _health(VERIFY_URL):
        p = subprocess.Popen(
            ["python", "-m", "uvicorn", "verification.main:app", "--port", "8040"],
            cwd=str(REPO_ROOT),
            env=_service_env("services/verification"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        procs.append(p)

    assert _wait_up(PORTAL_URL, 30), (
        f"Portal did not start at {PORTAL_URL}. "
        "Run 'alembic upgrade head' and check DATABASE_URL in .env."
    )
    assert _wait_up(VERIFY_URL, 30), (
        f"Verification API did not start at {VERIFY_URL}."
    )

    yield {"portal": PORTAL_URL, "verify": VERIFY_URL, "frontend": FRONTEND_URL}

    for p in procs:
        p.terminate()
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()


# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

@pytest.fixture
def test_bn() -> str:
    """Unique 9-char business number per test (avoids DB collisions)."""
    return f"E{secrets.token_hex(4).upper()}"


# ---------------------------------------------------------------------------
# Playwright — WebAuthn virtual authenticator
# ---------------------------------------------------------------------------

@pytest.fixture
def webauthn_page(browser, live_services):
    """
    Chromium page with a CDP virtual authenticator attached.
    The authenticator accepts any FIDO2 gesture automatically, replacing the
    real biometric/PIN prompt so tests run headlessly.
    """
    context = browser.new_context(base_url=FRONTEND_URL)
    page = context.new_page()

    cdp = context.new_cdp_session(page)
    cdp.send("WebAuthn.enable")
    cdp.send(
        "WebAuthn.addVirtualAuthenticator",
        {
            "options": {
                "protocol": "ctap2",
                "transport": "internal",
                "hasResidentKey": True,
                "hasUserVerification": True,
                "isUserVerified": True,
            }
        },
    )

    yield page

    context.close()
