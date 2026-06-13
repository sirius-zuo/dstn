"""
Browser e2e tests via Playwright + CDP WebAuthn virtual authenticator.

Each test gets a fresh virtual authenticator (via webauthn_page fixture) and a
unique business number (via test_bn fixture), so tests are fully isolated from
one another and from real data in the database.

The virtual authenticator silently handles all WebAuthn gestures — no biometric
prompt appears and no real device is required.

Prerequisites: the frontend dev server must be running at FRONTEND_URL
(default http://localhost:3000). The run_e2e.sh script starts it automatically.
"""
import pytest

from conftest import FRONTEND_URL, VERIFY_URL
import httpx


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _register(page, bn: str, timeout: int = 15_000) -> None:
    """Complete passkey registration flow for the given business number."""
    page.goto("/register")
    page.fill("#bn", bn)
    page.click("button:has-text('Register with Passkey')")
    page.wait_for_url("**/dashboard", timeout=timeout)


# ---------------------------------------------------------------------------
# Registration flow
# ---------------------------------------------------------------------------

def test_register_redirects_to_dashboard(webauthn_page, test_bn):
    """Successful passkey registration lands on the dashboard."""
    _register(webauthn_page, test_bn)
    assert "/dashboard" in webauthn_page.url


def test_dashboard_shows_pending_badge(webauthn_page, test_bn):
    """Before DAS sync the dashboard badge reads 'Credential Pending'."""
    _register(webauthn_page, test_bn)
    badge = webauthn_page.locator('[role="status"]')
    badge.wait_for(state="visible", timeout=5_000)
    assert "Pending" in badge.text_content()


def test_dashboard_has_logout_button(webauthn_page, test_bn):
    _register(webauthn_page, test_bn)
    assert webauthn_page.locator("button:has-text('Sign Out')").is_visible()


# ---------------------------------------------------------------------------
# Login flow (register first, then re-auth in the same authenticator session)
# ---------------------------------------------------------------------------

def test_login_after_register(webauthn_page, test_bn):
    """After registering, the supplier can sign in and reach the dashboard."""
    _register(webauthn_page, test_bn)

    # Logout
    webauthn_page.click("button:has-text('Sign Out')")
    webauthn_page.wait_for_url("**/login", timeout=5_000)

    # Login — virtual authenticator auto-selects the resident credential
    webauthn_page.click("button:has-text('Sign In with Passkey')")
    webauthn_page.wait_for_url("**/dashboard", timeout=15_000)

    assert "/dashboard" in webauthn_page.url
    webauthn_page.locator('[role="status"]').wait_for(state="visible", timeout=5_000)


# ---------------------------------------------------------------------------
# Language toggle
# ---------------------------------------------------------------------------

def test_dashboard_language_toggle(webauthn_page, test_bn):
    """Clicking the language button switches UI to French."""
    _register(webauthn_page, test_bn)

    # Default language is English — button shows 'FR'
    fr_button = webauthn_page.locator("button:has-text('FR')")
    fr_button.wait_for(state="visible", timeout=5_000)
    fr_button.click()

    # After toggle, button should now show 'EN'
    webauthn_page.locator("button:has-text('EN')").wait_for(state="visible", timeout=3_000)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_register_empty_bn_button_disabled(webauthn_page):
    """Register button is disabled when business number is empty."""
    webauthn_page.goto("/register")
    register_btn = webauthn_page.locator("button:has-text('Register with Passkey')")
    assert register_btn.is_disabled()


def test_unauthenticated_dashboard_redirects_to_login(webauthn_page):
    """Accessing /dashboard without a session redirects to /login."""
    # Clear any stale localStorage first
    webauthn_page.goto("/login")
    webauthn_page.evaluate("localStorage.removeItem('dstn_session_token')")
    webauthn_page.goto("/dashboard")
    webauthn_page.wait_for_url("**/login", timeout=5_000)
    assert "/login" in webauthn_page.url


# ---------------------------------------------------------------------------
# Post-registration verification API (cross-service)
# ---------------------------------------------------------------------------

def test_registered_bn_still_pending_on_verify_api(webauthn_page, test_bn, live_services):
    """
    After passkey registration, the verification API returns 'not_found' because
    a SupplierRecord is only created when the DAS sync cycle runs. This confirms
    the two services are decoupled and the verify endpoint does not expose unsynced
    registrations.
    """
    _register(webauthn_page, test_bn)

    r = httpx.get(f"{VERIFY_URL}/api/verify/{test_bn}")
    assert r.status_code == 200
    assert r.json()["status"] == "not_found"
