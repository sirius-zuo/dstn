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

## Step 9 — Run unit tests

All tests use SQLite in-memory and mocked HTTP — no Docker required.

```bash
# From the repo root:
cd services/das        && python -m pytest tests/ -v && cd ../..
cd services/issuer     && python -m pytest tests/ -v && cd ../..
cd services/portal     && python -m pytest tests/ -v && cd ../..
cd services/verification && python -m pytest tests/ -v && cd ../..
```

Expected: **48 tests, all passing**.

---

## Step 9b — Run automated E2E tests (optional)

The e2e suite uses Playwright + a CDP WebAuthn virtual authenticator so passkey flows run headlessly without a real device.

**Install e2e dependencies once:**

```bash
pip install -r requirements-e2e.txt
playwright install chromium
```

**Run everything via the orchestration script:**

```bash
bash scripts/run_e2e.sh
```

The script: starts Docker infra → runs migrations → starts portal/verification/frontend → runs `pytest tests/e2e/` → tears down processes it started.

**Or run the tests against already-running services:**

```bash
pytest tests/e2e/ -v                   # all e2e tests
pytest tests/e2e/ -v -k api            # API tests only (no browser)
pytest tests/e2e/ -v -k browser        # browser tests only
```

Service logs written to `.e2e-portal.log`, `.e2e-verification.log`, `.e2e-frontend.log` when started by the script.

---

## Step 10 — E2E smoke test walkthrough

With all services running:

### 10a. Verify a business number (before registration)
```bash
curl -s http://localhost:8040/api/verify/123456789 | python3 -m json.tool
# {"business_number": "123456789", "status": "not_found", "revoked": null}
```

### 10b. Register a passkey
Open **http://localhost:3000/register** in Chrome or Safari. Enter a CRA business number and click **Register with Passkey**. Your device prompts for biometric / PIN. On success you are redirected to `/dashboard`.

> WebAuthn requires a browser with platform authenticator support. It works in Chrome, Edge, Safari, and Firefox 119+. It does not work in headless or Selenium environments without a virtual authenticator.

### 10c. Check credential status before DAS sync
The dashboard shows **Credential Pending** — the DAS has not yet run for this business number.

### 10d. Trigger credential issuance manually
Run the one-shot sync (Terminal D above), or wait for the scheduled cycle. The DAS finds the supplier in CanadaBuys data, sets status to `active`, and calls the ACA-Py issuer agent.

```bash
cd services/das
python -c "import asyncio; from das.scheduler import run_sync_cycle; asyncio.run(run_sync_cycle())"
```

### 10e. Verify the issued credential
```bash
curl -s http://localhost:8040/api/verify/123456789 | python3 -m json.tool
# {"status": "active", "revoked": false, "business_number": "123456789", ...}
```

The dashboard also updates to show **GoC Verified Supplier**.

### 10f. Test the embedded widget
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

### 10g. Admin dashboard
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
