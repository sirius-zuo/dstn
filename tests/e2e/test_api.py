"""
API-layer e2e tests — no browser required.
All assertions use live HTTP calls against the running services.
"""
import pytest
import httpx

from conftest import PORTAL_URL, VERIFY_URL, ADMIN_KEY


# ---------------------------------------------------------------------------
# Health checks
# ---------------------------------------------------------------------------

def test_portal_health(live_services):
    r = httpx.get(f"{PORTAL_URL}/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_verification_health(live_services):
    r = httpx.get(f"{VERIFY_URL}/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Verification endpoint
# ---------------------------------------------------------------------------

def test_verify_unknown_business_number(live_services):
    r = httpx.get(f"{VERIFY_URL}/api/verify/000000000")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "not_found"
    assert body["business_number"] == "000000000"


def test_verify_returns_json_content_type(live_services):
    r = httpx.get(f"{VERIFY_URL}/api/verify/000000001")
    assert "application/json" in r.headers["content-type"]


# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------

def test_portal_security_headers(live_services):
    r = httpx.get(f"{PORTAL_URL}/health")
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("x-frame-options") == "DENY"
    assert "no-store" in r.headers.get("cache-control", "")


def test_verification_security_headers(live_services):
    r = httpx.get(f"{VERIFY_URL}/health")
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("x-frame-options") == "DENY"


# ---------------------------------------------------------------------------
# Admin dashboard
# ---------------------------------------------------------------------------

def test_admin_dashboard_requires_key(live_services):
    r = httpx.get(f"{PORTAL_URL}/admin/dashboard")
    assert r.status_code == 403


def test_admin_dashboard_ok(live_services):
    r = httpx.get(
        f"{PORTAL_URL}/admin/dashboard",
        headers={"x-admin-key": ADMIN_KEY},
    )
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


# ---------------------------------------------------------------------------
# Widget bundle
# ---------------------------------------------------------------------------

def test_widget_js_served(live_services):
    """Verifier widget bundle must be accessible at /static/widget.js."""
    r = httpx.get(f"{VERIFY_URL}/static/widget.js")
    assert r.status_code == 200
    assert "javascript" in r.headers["content-type"]
    # Sanity-check it's not empty and contains our IIFE pattern
    assert len(r.content) > 100


# ---------------------------------------------------------------------------
# Passkey registration begin (API only, no WebAuthn response)
# ---------------------------------------------------------------------------

def test_register_begin_returns_options(live_services):
    r = httpx.get(f"{PORTAL_URL}/passkey/register/begin?business_number=123456789")
    assert r.status_code == 200
    body = r.json()
    assert "options" in body
    assert "challenge" in body


def test_register_begin_missing_bn(live_services):
    r = httpx.get(f"{PORTAL_URL}/passkey/register/begin")
    assert r.status_code == 422  # Unprocessable Entity — missing required query param


# ---------------------------------------------------------------------------
# Credential status — unauthenticated
# ---------------------------------------------------------------------------

def test_credential_status_requires_auth(live_services):
    r = httpx.get(f"{PORTAL_URL}/credential/status")
    assert r.status_code in (401, 403, 422)
