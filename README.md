# DSTN — Decentralized Supplier Trust Network

DSTN is a Government of Canada system for issuing and verifying tamper-proof supplier credentials to registered businesses on the CanadaBuys procurement platform. Credentials are anchored on the Stratos decentralized infrastructure and held under supplier control via passkey-gated TEE wallets.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1 — Stratos Dcloud                                   │
│  did:stratos  ·  decentralized storage  ·  TEE compute      │
└───────────────────────┬─────────────────────────────────────┘
                        │ anchors DIDs, revocation
┌───────────────────────▼─────────────────────────────────────┐
│  Layer 2 — ACA-Py 0.11.x  +  AnonCreds 1.0                 │
│  Schema · CredDef · RevocationRegistry · Issue / Revoke     │
└───────────────────────┬─────────────────────────────────────┘
                        │ triggers
┌───────────────────────▼─────────────────────────────────────┐
│  Layer 2.5 — Data Aggregation Service (DAS)                 │
│  CanadaBuys · Open Government data  →  supplier status      │
└───────────┬───────────────────────────────────┬─────────────┘
            │ PENDING → ACTIVE / REVOKED        │
┌───────────▼────────────┐         ┌────────────▼─────────────┐
│  Layer 3 — Portal      │         │  Verification API         │
│  FastAPI + React 18    │         │  GET /api/verify/{bn}     │
│  Passkey Registry      │         │  Embedded widget (IIFE)   │
│  TEE Holder Agent      │         │                           │
│  Credential Store      │         │                           │
└────────────────────────┘         └──────────────────────────┘
```

### Key design decisions

- **did:key** derived from the supplier's WebAuthn P-256 COSE public key — no central identity authority
- **AES-256-GCM + HKDF** credential encryption at rest; key sealing delegates to the Stratos TEE SDK in production
- **AnonCreds revocation** checked on every `/verify` call via the ACA-Py revocation API
- **Passkey (FIDO2 / WebAuthn)** for supplier authentication — no passwords, no OTPs

---

## Services

| Service | Path | Port | Description |
|---|---|---|---|
| Data Aggregation Service | `services/das/` | — | Scheduled sync from CanadaBuys + Open Gov; triggers credential issuance |
| ACA-Py Issuer Agent | `services/issuer/` | 8020 / 8021 | AnonCreds issuance and revocation (runs in Docker) |
| Supplier Portal | `services/portal/` | 8030 | Passkey API, TEE credential holder, admin dashboard |
| Verification API | `services/verification/` | 8040 | Public verification endpoint + embedded widget bundle |
| Portal Frontend | `frontend/portal/` | 3000 | React 18 + TypeScript + Vite supplier-facing UI |
| Verifier Widget | `frontend/widget/` | — | Vanilla JS IIFE; build output → `services/verification/static/` |

---

## Quick start

See **[build.md](build.md)** for the full local e2e testing guide.

Short version:

```bash
# 1. Infrastructure
cp .env.example .env   # fill PORTAL_SECRET_KEY and Stratos credentials
docker compose up -d postgres redis issuer-agent

# 2. Python dependencies (uv workspace — installs all four services)
uv sync --all-packages

# 3. Database
alembic upgrade head

# 4. Bootstrap AnonCreds schema (once per environment)
cd services/issuer && python -m issuer.bootstrap && cd ../..

# 5. Build the verifier widget
cd frontend/widget && npm install && node build.js && cd ../..

# 6. Start services (four terminals)
uvicorn portal.main:app --port 8030 --app-dir services/portal --reload
uvicorn verification.main:app --port 8040 --app-dir services/verification --reload
cd services/das && python -m das.main

# 7. Frontend
cd frontend/portal && npm install && npm run dev
```

---

## API reference

### Portal — `http://localhost:8030`

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | — | Liveness check |
| `GET` | `/passkey/register/begin?business_number=BN` | — | Start WebAuthn registration |
| `POST` | `/passkey/register/complete` | — | Complete registration, return session token |
| `GET` | `/passkey/auth/begin` | — | Start WebAuthn authentication |
| `POST` | `/passkey/auth/complete` | — | Complete authentication, return session token |
| `GET` | `/credential/status` | Bearer JWT | Current credential status for authenticated supplier |
| `POST` | `/holder/receive` | Bearer JWT | Store an issued credential (called by issuer agent) |
| `GET` | `/admin/dashboard` | `x-admin-key` | HTML admin dashboard (supplier stats) |

### Verification API — `http://localhost:8040`

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | — | Liveness check |
| `GET` | `/api/verify/{business_number}` | — | Verify supplier credential status (public) |
| `GET` | `/static/widget.js` | — | Embedded verifier widget bundle |

#### Verification response shape

```json
{
  "business_number": "123456789",
  "status": "active",
  "revoked": false,
  "business_name": "Acme Widgets Inc.",
  "verified_at": "2026-06-12T14:30:00Z"
}
```

Possible `status` values: `active`, `pending`, `revoked`, `not_found`.

---

## Embedding the verifier widget

```html
<script src="https://dstn.canada.ca/static/widget.js"
        data-bn="123456789"
        data-api="https://dstn.canada.ca"
        integrity="sha384-REPLACE_WITH_ACTUAL_HASH"
        crossorigin="anonymous"
        async></script>
```

The widget renders a verified badge inline wherever the `<script>` tag appears. It reads live status from the Verification API on load.

---

## Running tests

All tests use SQLite in-memory and mocked HTTP — no Docker required.

```bash
cd services/das         && python -m pytest tests/ -v && cd ../..
cd services/issuer      && python -m pytest tests/ -v && cd ../..
cd services/portal      && python -m pytest tests/ -v && cd ../..
cd services/verification && python -m pytest tests/ -v && cd ../..
```

Expected: **48 tests, all passing**.

---

## Environment variables

See `.env.example` for the full list. Key variables:

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `PORTAL_SECRET_KEY` | 32-char secret for JWT signing |
| `PORTAL_RP_ID` | WebAuthn relying party ID (`localhost` for local dev) |
| `PORTAL_ORIGIN` | WebAuthn expected origin (`http://localhost:3000` for local dev) |
| `STRATOS_API_URL` | Stratos Dcloud REST API base URL |
| `STRATOS_API_KEY` | Stratos API key |
| `ISSUER_SCHEMA_ID` | AnonCreds schema ID (set after bootstrap) |
| `ISSUER_CRED_DEF_ID` | Credential definition ID (set after bootstrap) |
| `ISSUER_REV_REG_ID` | Revocation registry ID (set after bootstrap) |
| `ACAPY_WALLET_KEY` | ACA-Py wallet encryption key |
| `ADMIN_API_KEY` | `x-admin-key` for the portal admin dashboard |

---

## Deployment

Kubernetes manifests are in `deploy/k8s/`. Apply in order:

```bash
kubectl apply -f deploy/k8s/namespace.yml
kubectl apply -f deploy/k8s/configmap.yml
kubectl apply -f deploy/k8s/secrets.yml        # fill from secrets.yml.example first
kubectl apply -f deploy/k8s/das/
kubectl apply -f deploy/k8s/portal/
kubectl apply -f deploy/k8s/verification/
kubectl apply -f deploy/k8s/ingress.yml
```

Prometheus scrape config and alert rules are in `deploy/monitoring/`.

Target domain: `dstn.canada.ca` (configured in ingress).

---

## Tech stack

- **Python 3.12**, **FastAPI**, **SQLAlchemy 2.x async**, **Alembic**, **uv**
- **ACA-Py 0.11.x** (Aries Cloud Agent Python), **AnonCreds 1.0**
- **py_webauthn** (`webauthn` PyPI package) for FIDO2 / passkey flows
- **React 18**, **TypeScript**, **Vite**, `@simplewebauthn/browser`, `react-i18next`
- **PostgreSQL 16**, **Redis 7**
- **Docker Compose** for local infrastructure
- **Kubernetes** (namespace `dstn`) for production
- **Prometheus + Grafana** for monitoring

---

## Project structure

```
trustcan/
├── services/
│   ├── das/            # Data Aggregation Service
│   ├── issuer/         # ACA-Py issuer configuration + bootstrap
│   ├── portal/         # Supplier Portal backend
│   └── verification/   # Verification API
├── frontend/
│   ├── portal/         # React supplier portal
│   └── widget/         # Embedded verifier widget (IIFE)
├── shared/             # Pydantic config + SQLAlchemy models (shared across services)
├── deploy/
│   ├── k8s/            # Kubernetes manifests
│   └── monitoring/     # Prometheus config and alert rules
├── docker-compose.yml
├── pyproject.toml      # uv workspace root
├── .env.example
├── build.md            # Local e2e testing guide
└── README.md
```
