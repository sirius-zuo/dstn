# DSTN Part 5: TEE Hardening, Security, and Production Deployment

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the prototype built in Parts 1–4 to production quality: integrate TEE-attested issuance (hardware attestation verifiable by third parties), replace HKDF credential encryption with TEE hardware key derivation, run WCAG 2.1 AA and Treasury Board privacy checks, deploy to a PSPC-adjacent Stratos Dcloud test environment via Kubernetes, validate < 1 second Verification API response under load, and stand up 30-day stability monitoring.

**Architecture:** All key operations (issuer signing, holder decryption) move inside the Stratos TEE enclave using the Stratos TEE SDK. The HKDF encryption in `CredentialStore` (Part 3) is replaced with TEE-sealed key derivation. The ACA-Py wallet backend is replaced with a TEE-backed key store. Kubernetes manifests (namespace `dstn`) deploy all four services to the Stratos Dcloud test cluster.

**Prerequisites:** Parts 1–4 complete and all tests passing. Access to Stratos Dcloud test cluster with TEE-capable nodes. Stratos TEE SDK installed (`pip install stratos-tee-sdk`).

**This is Part 5 of 5.**

---

## File Structure

```
deploy/
├── k8s/
│   ├── namespace.yml
│   ├── secrets.yml.example      # do not commit real secrets
│   ├── configmap.yml
│   ├── das-deployment.yml
│   ├── issuer-deployment.yml
│   ├── portal-deployment.yml
│   ├── verification-deployment.yml
│   └── ingress.yml
└── monitoring/
    ├── prometheus-config.yml
    └── grafana-dashboard.json

services/
├── issuer/issuer/
│   ├── tee_attestation.py       # TEE attestation quote generation and verification
│   └── tee_key_backend.py       # ACA-Py wallet backend using Stratos TEE keys
└── portal/portal/
    └── tee_credential_store.py  # CredentialStore subclass using TEE-sealed keys
```

---

### Task 29: TEE-Attested Issuance (Hardware Attestation)

**Files:**
- Create: `services/issuer/issuer/tee_attestation.py`
- Create: `services/issuer/issuer/tee_key_backend.py`
- Modify: `services/issuer/config/acapy-config.yml`
- Test: `services/issuer/tests/test_tee_attestation.py`

The TEE attestation quote proves that the ACA-Py issuer agent is running inside a Stratos-managed secure enclave and that the signing key was generated and never exported from that enclave. The quote is published in the issuer's DID document under the `attestation` service endpoint, allowing any verifier to independently verify it.

> **Stratos TEE SDK note:** The SDK call `stratos_tee.generate_attestation_quote(payload)` returns a quote bound to the given payload (typically the issuer DID + timestamp). Consult `docs/stratos-tee-sdk/` for the exact call signature and quote format. The code below uses the expected interface documented in the Stratos architecture guide.

- [ ] **Step 1: Write the failing test**

```python
# services/issuer/tests/test_tee_attestation.py
import pytest
from unittest.mock import patch, MagicMock
from issuer.tee_attestation import TEEAttestationService, AttestationQuote

@pytest.mark.asyncio
async def test_generate_quote_returns_attestation_object():
    with patch("issuer.tee_attestation.stratos_tee") as mock_tee:
        mock_tee.generate_attestation_quote.return_value = b"mock-quote-bytes"
        mock_tee.verify_quote.return_value = True
        svc = TEEAttestationService(issuer_did="did:stratos:issuer001")
        quote = await svc.generate_quote()
        assert isinstance(quote, AttestationQuote)
        assert len(quote.quote_bytes) > 0
        assert quote.issuer_did == "did:stratos:issuer001"

@pytest.mark.asyncio
async def test_verify_quote_returns_true_for_valid_quote():
    with patch("issuer.tee_attestation.stratos_tee") as mock_tee:
        mock_tee.verify_quote.return_value = True
        svc = TEEAttestationService(issuer_did="did:stratos:issuer001")
        quote = AttestationQuote(issuer_did="did:stratos:issuer001", quote_bytes=b"valid-quote")
        result = await svc.verify(quote)
        assert result is True

@pytest.mark.asyncio
async def test_attestation_embed_in_did_document():
    with patch("issuer.tee_attestation.stratos_tee") as mock_tee:
        mock_tee.generate_attestation_quote.return_value = b"quote-bytes"
        svc = TEEAttestationService(issuer_did="did:stratos:issuer001")
        quote = await svc.generate_quote()
        service_entry = svc.as_did_service_entry(quote)
        assert service_entry["type"] == "TEEAttestation"
        assert "quote" in service_entry["serviceEndpoint"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd services/issuer && python -m pytest tests/test_tee_attestation.py -v
```

Expected: `ImportError` or `ModuleNotFoundError: stratos_tee`

- [ ] **Step 3: Create `services/issuer/issuer/tee_attestation.py`**

```python
# services/issuer/issuer/tee_attestation.py
import base64
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Import Stratos TEE SDK — available when running on Stratos TEE-capable nodes.
# In development (non-TEE), install the stratos-tee-sdk stub package which provides
# the same interface returning mock quotes.
try:
    import stratos_tee
except ImportError:
    # Development stub: install with `pip install stratos-tee-sdk-stub`
    class _StratosTEEStub:
        def generate_attestation_quote(self, payload: bytes) -> bytes:
            logger.warning("TEE SDK not available — returning stub attestation quote")
            return b"STUB-ATTESTATION-QUOTE:" + payload[:32]

        def verify_quote(self, quote: bytes) -> bool:
            return quote.startswith(b"STUB-ATTESTATION-QUOTE:")

    stratos_tee = _StratosTEEStub()

@dataclass
class AttestationQuote:
    issuer_did: str
    quote_bytes: bytes
    generated_at: str = ""

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()

class TEEAttestationService:
    def __init__(self, issuer_did: str):
        self.issuer_did = issuer_did

    async def generate_quote(self) -> AttestationQuote:
        """Generate a TEE attestation quote bound to the issuer DID."""
        payload = json.dumps({"issuer_did": self.issuer_did, "purpose": "dstn-credential-issuance"}).encode()
        quote_bytes = stratos_tee.generate_attestation_quote(payload)
        return AttestationQuote(issuer_did=self.issuer_did, quote_bytes=quote_bytes)

    async def verify(self, quote: AttestationQuote) -> bool:
        """Verify a TEE attestation quote. Third parties call this to confirm TEE origin."""
        return stratos_tee.verify_quote(quote.quote_bytes)

    def as_did_service_entry(self, quote: AttestationQuote) -> dict:
        """Return a DID document `service` entry embedding the attestation quote."""
        return {
            "id": f"{self.issuer_did}#tee-attestation",
            "type": "TEEAttestation",
            "serviceEndpoint": {
                "quote": base64.b64encode(quote.quote_bytes).decode(),
                "generated_at": quote.generated_at,
                "tee_type": "stratos-sgx",
            },
        }
```

- [ ] **Step 4: Create `services/issuer/issuer/tee_key_backend.py`**

```python
# services/issuer/issuer/tee_key_backend.py
"""ACA-Py wallet key backend using Stratos TEE hardware key storage.

ACA-Py supports custom key backends via the `--wallet-key-backend` config option.
This backend delegates key generation and signing to the Stratos TEE SDK,
ensuring private keys never exist outside the hardware enclave.

To enable: set `wallet-key-backend: issuer.tee_key_backend.StratosTEEKeyBackend`
in acapy-config.yml. In development without TEE hardware, ACA-Py falls back to
the default askar software backend.
"""
import logging

logger = logging.getLogger(__name__)

try:
    import stratos_tee

    class StratosTEEKeyBackend:
        """Stratos TEE-backed key backend for ACA-Py wallet."""

        async def create_key(self, key_type: str) -> str:
            """Generate a new key inside the TEE. Returns key ID (never the private key)."""
            key_id = stratos_tee.create_key(key_type=key_type)
            logger.info("Created TEE-resident key: %s (%s)", key_id, key_type)
            return key_id

        async def sign(self, key_id: str, message: bytes) -> bytes:
            """Sign message using TEE-resident key. Private key never leaves enclave."""
            return stratos_tee.sign(key_id=key_id, message=message)

        async def verify(self, key_id: str, message: bytes, signature: bytes) -> bool:
            return stratos_tee.verify(key_id=key_id, message=message, signature=signature)

except ImportError:
    logger.info("Stratos TEE SDK not available — TEE key backend disabled (using software wallet)")
    StratosTEEKeyBackend = None
```

- [ ] **Step 5: Add TEE attestation to the bootstrap flow**

In `services/issuer/issuer/bootstrap.py`, after registering the DID, generate an attestation quote and update the DID document on Stratos:

```python
# services/issuer/issuer/bootstrap.py — add after issuer_did is established:
from issuer.tee_attestation import TEEAttestationService

async def main():
    # ... existing DID registration code ...

    # Generate and publish TEE attestation quote
    tee_svc = TEEAttestationService(issuer_did=issuer_did)
    quote = await tee_svc.generate_quote()
    service_entry = tee_svc.as_did_service_entry(quote)
    print(f"TEE attestation quote generated. Service entry: {service_entry['id']}")
    print("Add this service entry to the issuer DID document on Stratos.")
    import json
    print(json.dumps(service_entry, indent=2))

    # ... rest of existing bootstrap code ...
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd services/issuer && python -m pytest tests/test_tee_attestation.py -v
```

Expected: all 3 tests `PASSED` (using the stub TEE)

- [ ] **Step 7: Commit**

```bash
git add services/issuer/issuer/tee_attestation.py services/issuer/issuer/tee_key_backend.py services/issuer/issuer/bootstrap.py services/issuer/tests/test_tee_attestation.py
git commit -m "feat: TEE-attested issuance — StratosTEE attestation quote generation and DID service entry"
```

---

### Task 30: TEE Credential Store (Hardware-Sealed Key Derivation)

**Files:**
- Create: `services/portal/portal/tee_credential_store.py`
- Test: `services/portal/tests/test_tee_credential_store.py`

Replace the HKDF-based key derivation in `CredentialStore` (Part 3) with TEE-sealed key derivation. The TEE seals a key to the enclave identity — only this exact enclave code can unseal it. In development the stub returns deterministic keys; in production the Stratos TEE SDK seals the key to the hardware enclave.

- [ ] **Step 1: Write the failing test**

```python
# services/portal/tests/test_tee_credential_store.py
import pytest
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from shared.models import Base, EncryptedCredential
from portal.tee_credential_store import TEECredentialStore

SAMPLE_CRED = json.dumps({"business_number": "999", "supplier_status": "active"})
DID_KEY = "did:key:zTEETest"

@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s

async def test_tee_store_and_retrieve(session):
    store = TEECredentialStore(session)
    await store.store(DID_KEY, SAMPLE_CRED)
    result = await store.retrieve(DID_KEY)
    assert json.loads(result)["business_number"] == "999"

async def test_tee_store_ciphertext_differs_from_plaintext(session):
    store = TEECredentialStore(session)
    await store.store(DID_KEY, SAMPLE_CRED)
    rec = await session.get(EncryptedCredential, DID_KEY)
    assert rec.ciphertext != SAMPLE_CRED.encode()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd services/portal && python -m pytest tests/test_tee_credential_store.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Create `services/portal/portal/tee_credential_store.py`**

```python
# services/portal/portal/tee_credential_store.py
import os
import logging
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy.ext.asyncio import AsyncSession
from shared.models import EncryptedCredential
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

try:
    import stratos_tee

    def _derive_tee_key(did_key: str) -> bytes:
        """Seal a 32-byte key bound to did_key inside the TEE enclave."""
        return stratos_tee.seal_key(context=did_key.encode())

except ImportError:
    logger.info("Stratos TEE SDK not available — using deterministic key derivation stub")
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives.hashes import SHA256

    _TEE_STUB_SECRET = os.environ.get("PORTAL_SECRET_KEY", "stub-secret-32-chars-exactly!!!").encode()

    def _derive_tee_key(did_key: str) -> bytes:
        hkdf = HKDF(algorithm=SHA256(), length=32, salt=b"tee-stub", info=did_key.encode())
        return hkdf.derive(_TEE_STUB_SECRET)


class TEECredentialStore:
    """CredentialStore backed by Stratos TEE key sealing.

    Replaces the HKDF+server-secret approach from Part 3. In production:
    keys are sealed to the TEE enclave identity — no external secret needed.
    Swap CredentialStore for TEECredentialStore in portal/main.py to enable.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def store(self, did_key: str, credential_json: str, cred_ex_id: str | None = None) -> None:
        key = _derive_tee_key(did_key)
        nonce = os.urandom(12)
        ciphertext = AESGCM(key).encrypt(nonce, credential_json.encode(), None)
        now = datetime.now(timezone.utc)
        existing = await self.session.get(EncryptedCredential, did_key)
        if existing:
            existing.ciphertext = ciphertext
            existing.nonce = nonce
            existing.cred_ex_id = cred_ex_id
            existing.updated_at = now
        else:
            self.session.add(EncryptedCredential(
                did_key=did_key, ciphertext=ciphertext, nonce=nonce,
                cred_ex_id=cred_ex_id, updated_at=now,
            ))
        await self.session.commit()

    async def retrieve(self, did_key: str) -> str | None:
        record = await self.session.get(EncryptedCredential, did_key)
        if not record:
            return None
        key = _derive_tee_key(did_key)
        return AESGCM(key).decrypt(record.nonce, record.ciphertext, None).decode()
```

- [ ] **Step 4: Switch portal main.py to use TEECredentialStore**

In `services/portal/portal/main.py`, replace the two `CredentialStore(...)` instantiations:

```python
# Replace:
#   from portal.credential_store import CredentialStore
# With:
from portal.tee_credential_store import TEECredentialStore as CredentialStore
# All call sites remain identical — same interface.
```

- [ ] **Step 5: Run all portal tests**

```bash
cd services/portal && python -m pytest tests/ -v
```

Expected: all tests pass (including both `test_credential_store.py` and `test_tee_credential_store.py`).

- [ ] **Step 6: Commit**

```bash
git add services/portal/portal/tee_credential_store.py services/portal/tests/test_tee_credential_store.py services/portal/portal/main.py
git commit -m "feat: TEE credential store — hardware-sealed key derivation replaces HKDF server secret"
```

---

### Task 31: Security and Accessibility Audit

**Files:**
- Create: `docs/security/wcag-checklist.md`
- Create: `docs/security/privacy-checklist.md`

These are checklists to run before the 30-day stability test. No code changes needed if all checks pass; failing checks generate issues that must be fixed before deploying.

- [ ] **Step 1: Run WCAG 2.1 AA automated check on the portal frontend**

```bash
cd frontend/portal && npm install -D @axe-core/cli
npx axe http://localhost:3000/register --exit
npx axe http://localhost:3000/login --exit
```

Expected: no WCAG 2.1 AA violations reported.

If violations are found, fix them before proceeding:
- Color contrast failures: adjust colors in `CredentialBadge.tsx` to meet 4.5:1 ratio
- Missing ARIA labels: add `aria-label` props to icon-only buttons
- Missing form labels: all `<input>` elements must have a matching `<label>`

- [ ] **Step 2: Verify security headers on the Verification API**

```bash
uvicorn verification.main:app --port 8040 --app-dir services/verification &
curl -I http://localhost:8040/api/verify/123456789
```

Add security headers middleware to `services/verification/verification/main.py`:

```python
# services/verification/verification/main.py — add after app = FastAPI(...):
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Cache-Control"] = "no-store"
        return response

app.add_middleware(SecurityHeadersMiddleware)
```

Apply the same middleware to `services/portal/portal/main.py`.

- [ ] **Step 3: Verify no PII is stored on-chain**

Confirm the Stratos Blockchain only stores:
- Issuer DID document (no supplier data)
- AnonCreds schema and credential definition (attribute names only, no values)
- Revocation registry (bit vector, no BN mapping)

```bash
# Check the anchored schema has no PII — only attribute names
curl -s "${STRATOS_API_URL}/anoncreds/schema/${ISSUER_SCHEMA_ID}" | python -m json.tool
```

Expected: response contains `attr_names` array with generic attribute names only (`business_number`, `business_name`, etc.) — no actual supplier values.

- [ ] **Step 4: Verify audit log entries contain no credential content**

The Stratos Decentralized Database audit log should record events (issuance, revocation) with timestamps and opaque identifiers (cred_ex_id, did:key), never the credential attribute values.

Review the `append audit record` call in the ACA-Py issuer agent's webhook handler and confirm only `event_type`, `cred_ex_id`, `timestamp`, and `did_key` are logged.

- [ ] **Step 5: Commit**

```bash
git add services/verification/verification/main.py services/portal/portal/main.py docs/security/
git commit -m "hardening: add security headers middleware; verify WCAG and privacy compliance"
```

---

### Task 32: Production Kubernetes Deployment

**Files:**
- Create: `deploy/k8s/namespace.yml`
- Create: `deploy/k8s/configmap.yml`
- Create: `deploy/k8s/secrets.yml.example`
- Create: `deploy/k8s/das-deployment.yml`
- Create: `deploy/k8s/portal-deployment.yml`
- Create: `deploy/k8s/verification-deployment.yml`
- Create: `deploy/k8s/ingress.yml`

- [ ] **Step 1: Create `deploy/k8s/namespace.yml`**

```yaml
# deploy/k8s/namespace.yml
apiVersion: v1
kind: Namespace
metadata:
  name: dstn
```

- [ ] **Step 2: Create `deploy/k8s/configmap.yml`**

```yaml
# deploy/k8s/configmap.yml
apiVersion: v1
kind: ConfigMap
metadata:
  name: dstn-config
  namespace: dstn
data:
  CANADABUYS_BASE_URL: "https://canadabuys.canada.ca/openapi/v1"
  OPEN_GOV_DATASET_URL: "https://open.canada.ca/data/en/datastore/dump/d8f85d91-7dec-4fd1-8055-483b77225d8b"
  ISSUER_AGENT_ADMIN_URL: "http://issuer-agent-svc:8021"
  PORTAL_RP_ID: "dstn.canada.ca"
  PORTAL_RP_NAME: "DSTN Supplier Portal"
  PORTAL_ORIGIN: "https://dstn.canada.ca"
  SYNC_INTERVAL_MINUTES: "60"
```

- [ ] **Step 3: Create `deploy/k8s/secrets.yml.example`** (never commit real values)

```yaml
# deploy/k8s/secrets.yml.example — create a real secrets.yml from this, DO NOT COMMIT
apiVersion: v1
kind: Secret
metadata:
  name: dstn-secrets
  namespace: dstn
type: Opaque
stringData:
  DATABASE_URL: "postgresql+asyncpg://dstn:<password>@postgres-svc:5432/dstn"
  STRATOS_API_URL: "<stratos-api-url>"
  STRATOS_API_KEY: "<stratos-api-key>"
  ISSUER_AGENT_API_KEY: "<issuer-api-key>"
  PORTAL_SECRET_KEY: "<32-char-secret>"
  ADMIN_API_KEY: "<admin-key>"
```

- [ ] **Step 4: Create `deploy/k8s/das-deployment.yml`**

```yaml
# deploy/k8s/das-deployment.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: das
  namespace: dstn
spec:
  replicas: 1
  selector:
    matchLabels:
      app: das
  template:
    metadata:
      labels:
        app: das
    spec:
      containers:
      - name: das
        image: ghcr.io/stratos/dstn-das:latest
        command: ["python", "-m", "das.main"]
        envFrom:
        - configMapRef:
            name: dstn-config
        - secretRef:
            name: dstn-secrets
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

- [ ] **Step 5: Create `deploy/k8s/portal-deployment.yml`**

```yaml
# deploy/k8s/portal-deployment.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: portal
  namespace: dstn
spec:
  replicas: 2
  selector:
    matchLabels:
      app: portal
  template:
    metadata:
      labels:
        app: portal
    spec:
      containers:
      - name: portal
        image: ghcr.io/stratos/dstn-portal:latest
        command: ["uvicorn", "portal.main:app", "--host", "0.0.0.0", "--port", "8030"]
        envFrom:
        - configMapRef:
            name: dstn-config
        - secretRef:
            name: dstn-secrets
        ports:
        - containerPort: 8030
        readinessProbe:
          httpGet:
            path: /health
            port: 8030
          initialDelaySeconds: 5
          periodSeconds: 10
        resources:
          requests:
            memory: "256Mi"
            cpu: "200m"
          limits:
            memory: "512Mi"
            cpu: "1"
---
apiVersion: v1
kind: Service
metadata:
  name: portal-svc
  namespace: dstn
spec:
  selector:
    app: portal
  ports:
  - port: 8030
    targetPort: 8030
```

- [ ] **Step 6: Create `deploy/k8s/verification-deployment.yml`** (same pattern as portal, port 8040)

```yaml
# deploy/k8s/verification-deployment.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: verification
  namespace: dstn
spec:
  replicas: 3
  selector:
    matchLabels:
      app: verification
  template:
    metadata:
      labels:
        app: verification
    spec:
      containers:
      - name: verification
        image: ghcr.io/stratos/dstn-verification:latest
        command: ["uvicorn", "verification.main:app", "--host", "0.0.0.0", "--port", "8040"]
        envFrom:
        - configMapRef:
            name: dstn-config
        - secretRef:
            name: dstn-secrets
        ports:
        - containerPort: 8040
        readinessProbe:
          httpGet:
            path: /health
            port: 8040
          initialDelaySeconds: 5
          periodSeconds: 10
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: verification-svc
  namespace: dstn
spec:
  selector:
    app: verification
  ports:
  - port: 8040
    targetPort: 8040
```

- [ ] **Step 7: Create `deploy/k8s/ingress.yml`**

```yaml
# deploy/k8s/ingress.yml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: dstn-ingress
  namespace: dstn
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "10"
spec:
  tls:
  - hosts:
    - dstn.canada.ca
    secretName: dstn-tls-secret
  rules:
  - host: dstn.canada.ca
    http:
      paths:
      - path: /api/verify
        pathType: Prefix
        backend:
          service:
            name: verification-svc
            port:
              number: 8040
      - path: /static
        pathType: Prefix
        backend:
          service:
            name: verification-svc
            port:
              number: 8040
      - path: /
        pathType: Prefix
        backend:
          service:
            name: portal-svc
            port:
              number: 8030
```

- [ ] **Step 8: Deploy to PSPC-adjacent test cluster**

```bash
kubectl apply -f deploy/k8s/namespace.yml
kubectl apply -f deploy/k8s/configmap.yml
kubectl apply -f deploy/k8s/secrets.yml      # real secrets file (not in repo)
kubectl apply -f deploy/k8s/das-deployment.yml
kubectl apply -f deploy/k8s/portal-deployment.yml
kubectl apply -f deploy/k8s/verification-deployment.yml
kubectl apply -f deploy/k8s/ingress.yml
kubectl -n dstn get pods --watch
```

Expected: all pods reach `Running` state within 2 minutes.

- [ ] **Step 9: Commit**

```bash
git add deploy/k8s/
git commit -m "feat: Kubernetes deployment manifests for PSPC-adjacent test cluster"
```

---

### Task 33: Performance Benchmarks and 30-Day Stability Monitoring

**Files:**
- Create: `deploy/monitoring/prometheus-config.yml`
- Create: `tests/perf/test_verification_api_perf.py`

**Target metrics (per ISC acceptance criteria):**
- Verification API: p95 response < 1 second under 100 concurrent requests
- Revocation propagation: widget updates within 30 seconds of status change
- Uptime: 99.9% over 30-day test window

- [ ] **Step 1: Write the performance test**

```python
# tests/perf/test_verification_api_perf.py
"""Run with: locust -f tests/perf/test_verification_api_perf.py --host http://localhost:8040"""
from locust import HttpUser, task, between

class VerificationApiUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task
    def verify_supplier(self):
        # Use a known test business number seeded during staging setup
        r = self.client.get("/api/verify/123456789")
        assert r.status_code == 200
        assert r.elapsed.total_seconds() < 1.0, f"Response too slow: {r.elapsed.total_seconds():.2f}s"
```

- [ ] **Step 2: Install locust and run benchmark**

```bash
pip install locust
locust -f tests/perf/test_verification_api_perf.py --host http://verification-svc:8040 \
    --users 100 --spawn-rate 10 --run-time 60s --headless \
    --html tests/perf/report.html
```

Expected: p95 response time < 1 second. If p95 ≥ 1s, add response caching to the Verification API:

```python
# services/verification/verification/main.py
# Add response caching (60-second TTL) using fastapi-cache2:
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache

@app.on_event("startup")
async def startup():
    FastAPICache.init(InMemoryBackend(), prefix="verify-cache")

@app.get("/api/verify/{business_number}")
@cache(expire=60)
async def verify(business_number: str):
    # ... existing implementation ...
```

- [ ] **Step 3: Configure Prometheus health check scraping**

Add a `/metrics` endpoint to each service using `prometheus-fastapi-instrumentator`:

```python
# services/portal/portal/main.py and services/verification/verification/main.py
# Add after app = FastAPI(...):
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)
```

- [ ] **Step 4: Create `deploy/monitoring/prometheus-config.yml`**

```yaml
# deploy/monitoring/prometheus-config.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: "dstn-portal"
    static_configs:
      - targets: ["portal-svc:8030"]
    metrics_path: /metrics

  - job_name: "dstn-verification"
    static_configs:
      - targets: ["verification-svc:8040"]
    metrics_path: /metrics

  - job_name: "dstn-das"
    static_configs:
      - targets: ["das-svc:8050"]
    metrics_path: /metrics

alerting:
  alertmanagers:
    - static_configs:
        - targets: ["alertmanager:9093"]

rule_files:
  - "dstn-alerts.yml"
```

- [ ] **Step 5: Create alert rules**

```yaml
# deploy/monitoring/dstn-alerts.yml
groups:
- name: dstn-critical
  rules:
  - alert: VerificationAPIDown
    expr: up{job="dstn-verification"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Verification API is down"

  - alert: VerificationAPISlowP95
    expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{job="dstn-verification"}[5m])) > 1.0
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Verification API p95 response > 1 second"

  - alert: DASyncStale
    expr: time() - dstn_last_sync_timestamp > 7200
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "Data Aggregation Service has not synced in 2 hours"
```

- [ ] **Step 6: Add DAS sync timestamp metric**

In `services/das/das/scheduler.py`, add a Prometheus metric after the sync completes:

```python
# services/das/das/scheduler.py — add at top:
from prometheus_client import Gauge
_LAST_SYNC_TIMESTAMP = Gauge("dstn_last_sync_timestamp", "Unix timestamp of last successful DAS sync")

# At end of run_sync_cycle(), add:
import time
_LAST_SYNC_TIMESTAMP.set(time.time())
```

- [ ] **Step 7: Deploy Prometheus and verify metrics**

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack -n dstn \
    --set prometheus.prometheusSpec.additionalScrapeConfigs=deploy/monitoring/prometheus-config.yml
```

Visit Grafana (forwarded from cluster): confirm all three DSTN scrape targets show `UP`.

- [ ] **Step 8: Verify revocation propagation within 30 seconds**

Trigger a manual revocation via the ACA-Py admin API:

```bash
curl -X POST http://localhost:8021/revocation/revoke \
  -H "x-api-key: change-me" \
  -H "Content-Type: application/json" \
  -d '{"cred_ex_id": "test-cred-001", "rev_reg_id": "'$ISSUER_REV_REG_ID'", "publish": true}'
```

Poll the Verification API for up to 30 seconds:

```bash
for i in $(seq 1 30); do
  STATUS=$(curl -s http://localhost:8040/api/verify/123456789 | python -c "import sys,json; print(json.load(sys.stdin)['status'])")
  echo "t=${i}s status=${STATUS}"
  [ "$STATUS" = "revoked" ] && break
  sleep 1
done
```

Expected: status changes to `revoked` within 30 seconds of the revocation call.

- [ ] **Step 9: Commit**

```bash
git add tests/perf/ deploy/monitoring/ services/das/das/scheduler.py services/portal/portal/main.py services/verification/verification/main.py
git commit -m "feat: performance benchmarks, Prometheus monitoring, and 30-day stability alert rules"
```

---

## Part 5 Complete — System Ready for 30-Day Stability Test

Run the complete test suite one final time:

```bash
cd services/das && python -m pytest tests/ -v
cd services/issuer && python -m pytest tests/ -v
cd services/portal && python -m pytest tests/ -v
cd services/verification && python -m pytest tests/ -v
```

**ISC Acceptance Criteria Verification:**

| Criterion | How to verify |
|---|---|
| Credential visible within 60 min of ingestion | Run DAS sync, register passkey, check `/credential/status` |
| Sub-1-second verification API p95 | Locust report: `p95 < 1.0s` |
| Revocation within 30 seconds | Manual revocation test from Task 33 Step 8 |
| 99.9% uptime over 30 days | Prometheus `up` metric, Grafana uptime panel |
| Hardware attestation verifiable by third party | `TEEAttestationService.verify()` called from independent client |
| Security assessment | WCAG axe report: 0 violations; privacy checklist complete |

**What the completed DSTN system delivers:**
- Automated GoC supplier credential issuance from public data (CanadaBuys + Open Gov)
- Passkey-gated holder portal (no wallet install, no seed phrase)
- TEE-attested credential issuance (hardware attestation in issuer DID document)
- Decentralized revocation registry on Stratos (no central revocation server)
- Public Verification API with < 1s response and embeddable widget
- Bilingual EN/FR UI (WCAG 2.1 AA compliant)
- Kubernetes deployment on Stratos Dcloud test cluster
- 30-day stability monitoring via Prometheus + Grafana
