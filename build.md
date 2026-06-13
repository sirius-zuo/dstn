# Local E2E Testing Environment

This guide brings up the full DSTN stack on your machine: PostgreSQL, Redis, the ACA-Py issuer agent, all four Python services, and the React frontend. End-to-end passkey registration → credential issuance → verification works when all steps complete.

## Prerequisites

| Tool | Min version | Install |
|---|---|---|
| Python | 3.12 | `brew install python@3.12` or [python.org](https://python.org) |
| uv | 0.4+ | `curl -Ls https://astral.sh/uv/install.sh \| sh` |
| Node.js | 18 | `brew install node` or [nodejs.org](https://nodejs.org) |
| Docker Desktop | 4.x | [docker.com/products/docker-desktop](https://docker.com/products/docker-desktop) |
| Git | any | |

WebAuthn only works over `localhost` (or HTTPS). Do not change `PORTAL_RP_ID` / `PORTAL_ORIGIN` for local testing.

---

## Step 1 — Clone and configure environment

```bash
git clone <repo-url> trustcan
cd trustcan

cp .env.example .env
```

Open `.env` and fill in the values marked `change-me`. For local testing the minimum required changes are:

```bash
# Generate a 32-char random secret for JWT signing:
PORTAL_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(16))")

# Stratos access — required for DID anchoring, schema, revocation.
# If you don't have Stratos credentials yet, services start but DAS sync
# and credential issuance will fail gracefully (see "Without Stratos" note below).
STRATOS_API_URL=https://stratos-api.thestratos.org/api/v1
STRATOS_API_KEY=<your-stratos-key>
```

Leave everything else at the defaults for local development.

---

## Step 2 — Start infrastructure

```bash
docker compose up -d postgres redis
```

Wait for Postgres to be healthy:

```bash
docker compose ps        # postgres should show "(healthy)"
```

The ACA-Py issuer agent also runs in Docker. Build and start it:

```bash
docker compose up -d issuer-agent
```

Wait ~20 seconds for ACA-Py to finish initializing, then verify:

```bash
curl -s -H "x-api-key: change-me" http://localhost:8021/status | python3 -m json.tool
# Should return {"version": "0.11.x", "ready": true, ...}
```

---

## Step 3 — Install Python dependencies

From the repo root (uv workspace installs all four services at once):

```bash
uv sync --all-packages
```

---

## Step 4 — Run database migrations

```bash
alembic upgrade head
```

This creates all tables (`supplier_records`, `passkey_records`, `encrypted_credentials`) in the local Postgres instance.

---

## Step 5 — Bootstrap AnonCreds schema and credential definition

This step anchors the GoC Supplier schema, credential definition, and revocation registry on Stratos. It only needs to run once per environment.

```bash
cd services/issuer
python -m issuer.bootstrap
```

The script prints three IDs. Copy them into your `.env`:

```bash
ISSUER_SCHEMA_ID=did:stratos:issuer001/anoncreds/v0/SCHEMA/GoCSupplierCredential/1.0
ISSUER_CRED_DEF_ID=did:stratos:issuer001/anoncreds/v0/CLAIM_DEF/...
ISSUER_REV_REG_ID=did:stratos:issuer001/anoncreds/v0/REV_REG_DEF/...
```

Return to the repo root:

```bash
cd ../..
```

---

## Step 6 — Build the verifier widget

```bash
cd frontend/widget
npm install
node build.js
cd ../..
```

This writes the minified bundle to `services/verification/static/widget.js`, which the Verification API serves at `/static/widget.js`.

---

## Step 7 — Start the Python services

Open **four terminals** (or use a process manager like `overmind` / `honcho`).

**Terminal A — Portal backend (passkey + credential API):**
```bash
uvicorn portal.main:app --port 8030 --app-dir services/portal --reload
```

**Terminal B — Verification API:**
```bash
uvicorn verification.main:app --port 8040 --app-dir services/verification --reload
```

**Terminal C — Data Aggregation Service (runs sync on schedule):**
```bash
cd services/das
python -m das.main
```

**Terminal D — (optional) DAS one-shot sync to seed data immediately:**
```bash
cd services/das
python -c "import asyncio; from das.scheduler import run_sync_cycle; asyncio.run(run_sync_cycle())"
```

Health checks:

```bash
curl http://localhost:8030/health    # {"status":"ok"}
curl http://localhost:8040/health    # {"status":"ok"}
```

---

## Step 8 — Start the React portal frontend

```bash
cd frontend/portal
npm install
npm run dev
```

Opens at **http://localhost:3000**. Vite proxies `/passkey`, `/credential`, and `/holder` requests to the portal backend at `:8030`.

---

## Step 9 — Unit tests

Unit tests are self-contained: SQLite in-memory database, all external HTTP mocked with `respx`. No Docker, no Stratos credentials, no running services needed.

```bash
cd services/das         && python -m pytest tests/ -v && cd ../..
cd services/issuer      && python -m pytest tests/ -v && cd ../..
cd services/portal      && python -m pytest tests/ -v && cd ../..
cd services/verification && python -m pytest tests/ -v && cd ../..
```

Expected: **48 tests, all passing**.

---

## Step 10 — Automated E2E tests

The automated e2e suite exercises the full stack end-to-end — live Postgres, live HTTP services, and a real Chromium browser. It lives in `tests/e2e/`.

### How it works

**Two test files, two layers:**

| File | What it tests | Requires browser? |
|---|---|---|
| `tests/e2e/test_api.py` | Health endpoints, `/api/verify`, admin dashboard, widget bundle, security headers, passkey registration begin | No — httpx only |
| `tests/e2e/test_browser.py` | Passkey register → dashboard, logout → login, language toggle, disabled-button guard, unauthenticated redirect | Yes — Playwright + Chromium |

**WebAuthn virtual authenticator**

Real passkey flows require a platform authenticator (Face ID, Touch ID, Windows Hello). The e2e tests replace this with a Chrome DevTools Protocol (CDP) virtual authenticator injected at test start:

```
test starts
  └─ conftest creates Chromium context
       └─ CDP WebAuthn.enable + addVirtualAuthenticator
            └─ virtual authenticator stores/replays FIDO2 credentials in-process
                 └─ startRegistration / startAuthentication complete silently
                      └─ portal backend verifies the signature normally
```

No mocking happens at the HTTP or application level — the portal receives and verifies real WebAuthn responses. The only difference from a real device is that the biometric prompt never appears.

**Test isolation**

Each browser test gets a fresh Chromium context (new virtual authenticator, empty credential store) and a fresh random business number (`E` + 8 hex chars). Tests cannot share or corrupt each other's passkey state.

**Service management**

The `live_services` fixture (session-scoped) checks whether the portal and verification API are already up. If they are, it reuses them. If not, it starts them as subprocesses and tears them down after all tests finish. The frontend is managed separately by `run_e2e.sh`.

---

### One-command run

Install e2e dependencies once:

```bash
pip install -r requirements-e2e.txt
playwright install chromium
```

Then run everything:

```bash
bash scripts/run_e2e.sh
```

What the script does, in order:

1. Checks that `python`, `docker`, `npm`, and `node` are on `$PATH`
2. Installs e2e Python deps and Chromium if not already installed
3. `docker compose up -d postgres redis`
4. Waits for Postgres to pass `pg_isready`
5. `alembic upgrade head`
6. Starts portal backend on `:8030` (if not already running)
7. Starts verification API on `:8040` (if not already running)
8. Builds the verifier widget if `services/verification/static/widget.js` is missing
9. `npm run dev` for the React frontend on `:3000` (if not already running)
10. `pytest tests/e2e/ --browser chromium -v` (plus any extra args you pass)
11. Kills all processes it started

Service stdout is redirected to log files in the repo root:

```
.e2e-portal.log
.e2e-verification.log
.e2e-frontend.log
```

Check these if a service fails to start.

---

### Running against already-running services

If you already have the stack up from Steps 7–8, skip `run_e2e.sh` and run pytest directly:

```bash
# All e2e tests
pytest tests/e2e/ -v

# API tests only (fast, no Chromium launch)
pytest tests/e2e/ -v -k api

# Browser tests only
pytest tests/e2e/ -v -k browser

# Single test
pytest tests/e2e/test_browser.py::test_register_redirects_to_dashboard -v
```

`tests/e2e/pytest.ini` sets `--browser chromium` automatically, so you don't need to pass it manually.

---

### What each test covers

**`test_api.py`** (11 tests)

| Test | Checks |
|---|---|
| `test_portal_health` | `GET /health` → `{"status":"ok"}` |
| `test_verification_health` | `GET /health` → `{"status":"ok"}` |
| `test_verify_unknown_business_number` | `/api/verify/000000000` → `status: not_found` |
| `test_verify_returns_json_content_type` | `content-type: application/json` |
| `test_portal_security_headers` | `X-Content-Type-Options`, `X-Frame-Options`, `Cache-Control` |
| `test_verification_security_headers` | Same headers on verification API |
| `test_admin_dashboard_requires_key` | Missing `x-admin-key` → 403 |
| `test_admin_dashboard_ok` | Valid `x-admin-key` → 200 HTML |
| `test_widget_js_served` | `/static/widget.js` → 200, non-empty JS |
| `test_register_begin_returns_options` | `/passkey/register/begin` → `options` + `challenge` |
| `test_register_begin_missing_bn` | Missing `business_number` param → 422 |
| `test_credential_status_requires_auth` | No `Authorization` header → 401/403/422 |

**`test_browser.py`** (8 tests)

| Test | Covers |
|---|---|
| `test_register_redirects_to_dashboard` | Passkey registration completes, lands on `/dashboard` |
| `test_dashboard_shows_pending_badge` | Badge reads "Credential Pending" before DAS sync |
| `test_dashboard_has_logout_button` | "Sign Out" button is visible |
| `test_login_after_register` | Logout then re-authenticate → back on dashboard |
| `test_dashboard_language_toggle` | Click FR → button switches to EN (i18n works) |
| `test_register_empty_bn_button_disabled` | Register button disabled when input is empty |
| `test_unauthenticated_dashboard_redirects_to_login` | No session token → `/dashboard` redirects to `/login` |
| `test_registered_bn_still_pending_on_verify_api` | After passkey registration, `/api/verify/{bn}` returns `not_found` — confirms DAS sync is required for credential status |

---

### Common e2e failures

**`AssertionError: Portal did not start`**

The portal process failed to bind. Check `.e2e-portal.log`. Most common cause: `DATABASE_URL` in `.env` is wrong or Postgres isn't healthy yet. Run `docker compose ps` and verify `alembic upgrade head` succeeded.

**`TimeoutError` on `page.wait_for_url('**/dashboard')`**

The WebAuthn flow timed out. Possible causes:
- Not using Chromium (`--browser chromium` is required for the CDP virtual authenticator; Firefox/WebKit don't support it)
- The `PORTAL_RP_ID` or `PORTAL_ORIGIN` in `.env` doesn't match `localhost`/`http://localhost:3000`
- The portal returned an error — check `.e2e-portal.log`

**`playwright._impl._errors.Error: Target page, context or browser has been closed`**

A test closed the browser context before a fixture teardown. This is safe to ignore if all assertions passed; it's a cleanup race, not a real failure.

**Widget test fails: `AssertionError: 200 != 404`**

The widget bundle hasn't been built yet. Run:
```bash
cd frontend/widget && npm install && node build.js && cd ../..
```

---

## Step 11 — Manual smoke test walkthrough

With all services running:

### 11a. Verify a business number (before registration)
```bash
curl -s http://localhost:8040/api/verify/123456789 | python3 -m json.tool
# {"business_number": "123456789", "status": "not_found", "revoked": null}
```

### 11b. Register a passkey
Open **http://localhost:3000/register** in Chrome or Safari. Enter a CRA business number and click **Register with Passkey**. Your device prompts for biometric / PIN. On success you are redirected to `/dashboard`.

> WebAuthn requires a browser with platform authenticator support. It works in Chrome, Edge, Safari, and Firefox 119+. It does not work in headless or Selenium environments without a virtual authenticator.

### 11c. Check credential status before DAS sync
The dashboard shows **Credential Pending** — the DAS has not yet run for this business number.

### 11d. Trigger credential issuance manually
Run the one-shot sync (Terminal D above), or wait for the scheduled cycle. The DAS finds the supplier in CanadaBuys data, sets status to `active`, and calls the ACA-Py issuer agent.

```bash
cd services/das
python -c "import asyncio; from das.scheduler import run_sync_cycle; asyncio.run(run_sync_cycle())"
```

### 11e. Verify the issued credential
```bash
curl -s http://localhost:8040/api/verify/123456789 | python3 -m json.tool
# {"status": "active", "revoked": false, "business_number": "123456789", ...}
```

The dashboard also updates to show **GoC Verified Supplier**.

### 11f. Test the embedded widget
```bash
curl -s http://localhost:8040/static/widget.js | head -3
# (minified JS)
```

Create a test HTML file:
```html
<!DOCTYPE html>
<html>
<body>
  <script src="http://localhost:8040/static/widget.js"
          data-bn="123456789"
          data-api="http://localhost:8040"
          async></script>
</body>
</html>
```
Open it in a browser — the badge renders with live status.

### 11g. Admin dashboard
```bash
curl -H "x-admin-key: change-admin-key" http://localhost:8030/admin/dashboard
# HTML page with supplier counts and recent records
```

---

## Service ports reference

| Service | Port | Purpose |
|---|---|---|
| Portal backend | 8030 | Passkey API, credential status, admin dashboard |
| Verification API | 8040 | Public `GET /api/verify/{bn}`, widget bundle |
| ACA-Py DIDComm | 8020 | DIDComm agent endpoint |
| ACA-Py admin | 8021 | Internal admin API (no public access) |
| Portal frontend | 3000 | React dev server (Vite) |
| PostgreSQL | 5432 | Shared DB for all services |
| Redis | 6379 | (loopback only) Cache / future challenge store |

---

## Without Stratos credentials

If you don't have Stratos API access, the system degrades gracefully:

- **Portal** starts and serves WebAuthn flows — passkeys register fine.
- **DAS sync** runs but the `CredentialTrigger` fails to reach ACA-Py's `/connections` endpoint; suppliers remain in `PENDING_REGISTRATION`.
- **Verification API** returns `status: pending` for all registered suppliers.

Unit tests are fully independent of Stratos (all external calls are mocked with `respx`).

---

## Resetting the local environment

```bash
# Wipe the database and start fresh
docker compose down -v        # removes the pgdata volume
docker compose up -d postgres redis
alembic upgrade head
```

---

## Common issues

**`webauthn` import error on portal startup**
```bash
cd services/portal && uv pip install webauthn
```

**ACA-Py returns `{"ready": false}`**
Wait 30 seconds after `docker compose up -d issuer-agent` — the agent takes time to initialize the wallet on first boot.

**Passkey registration fails with "challenge mismatch"**
Ensure `PORTAL_RP_ID=localhost` and `PORTAL_ORIGIN=http://localhost:3000` in `.env`. Any other hostname breaks WebAuthn on HTTP.

**Port already in use**
```bash
lsof -i :8030    # find the PID
kill <PID>
```

**Alembic "can't connect to database"**
Confirm Postgres is healthy: `docker compose ps`. Check `DATABASE_URL` in `.env` matches the Docker Compose credentials (default: `dstn`/`dstn`).
