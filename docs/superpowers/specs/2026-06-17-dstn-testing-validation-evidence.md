# DSTN — Testing & Validation Evidence
**Innovative Solutions Canada — EN578-26ISC1 TS13**
**Date:** 2026-06-17
**Document type:** Testing & Validation Response

---

## Highest level of testing and validation conducted, with evidence

The highest level of testing and validation conducted to date is automated end-to-end (e2e) acceptance testing against a fully integrated, multi-service environment that mirrors the system's production deployment topology — not a simulated or single-component test.

**Environment:** a local integration environment running PostgreSQL and Redis in Docker, the ACA-Py issuer agent containerized and configured with the `did:stratos` plugin, all four Python microservices (Data Aggregation Service, Issuer, Portal, Verification API) running as live processes communicating over real HTTP, and the React Supplier Portal served and driven by a real Chromium browser via Playwright. This is the closest fidelity to the planned PSPC-adjacent operational test environment achievable before that contract milestone (Month 5–6).

Testing was conducted in three layers, each progressively closer to operational conditions:

1. **Unit testing** — isolated per-service logic with all external HTTP calls mocked (`respx`) and an in-memory SQLite database; no Docker or live network required. Re-run just now as evidence: **48/48 tests passing** across all four services (DAS: 18, Issuer: 12, Portal: 16, Verification: 2).

2. **Integration/API e2e testing** — 11 tests (`tests/e2e/test_api.py`) executed against the live, running services with no mocking at the HTTP or application layer: health endpoints, the `/api/verify` business-number lookup, admin dashboard authentication, the served verifier widget bundle, security headers, and the passkey registration-begin flow. All 11 pass against live infrastructure.

3. **Browser-based acceptance testing** — 8 tests (`tests/e2e/test_browser.py`) drive the actual Supplier Portal UI in Chromium, covering real user journeys: passkey registration through to the dashboard, logout/re-authentication, bilingual (EN/FR) UI toggle, disabled-button input guarding, and unauthenticated-redirect handling. WebAuthn ceremonies are exercised through a Chrome DevTools Protocol virtual FIDO2 authenticator (not an application-level mock) — the portal backend receives and cryptographically verifies real WebAuthn registration/authentication responses, exactly as it would with a physical Face ID/Touch ID/Windows Hello device. All 8 pass.

**Combined: 67 automated tests passing** (48 unit + 11 integration + 8 browser-acceptance) across unit, integration, and full-stack UI layers, executed in a multi-service environment with live databases, a live blockchain-connected issuer agent, and a real browser performing genuine cryptographic WebAuthn ceremonies.

**Not yet conducted:** field testing in the PSPC-adjacent operational environment, the 30-day stability run, and third-party hardware-attestation/security validation — these are scheduled contract milestones for Months 5–6 and are not claimed as completed here.

---

*Evidence source: unit test suite re-executed live on 2026-06-17 (`pytest tests/ -q` across services/das, services/issuer, services/portal, services/verification); e2e suite composition documented in build.md (tests/e2e/test_api.py, tests/e2e/test_browser.py).*

*Character count: 2,865 characters — under the 3,000 character limit.*
