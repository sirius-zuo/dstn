# DSTN Part 2: Credential Protocol Layer

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the Aries Issuer Agent (ACA-Py), anchor the AnonCreds schema and credential definition on the Stratos Blockchain, implement the `did:stratos` DID resolver plugin, manage the revocation registry, and wire the full Credential Trigger so the DAS from Part 1 can issue and revoke real credentials.

**Architecture:** ACA-Py runs as a Docker service with a custom `did:stratos` resolver plugin. A `StratosClient` class wraps the Stratos blockchain REST API for DID anchoring, schema registration, and revocation registry operations. The DAS CredentialTrigger (stubbed in Part 1) is filled in with the correct payload — schema ID, cred def ID, and holder connection IDs — once those are anchored.

**Tech Stack:** ACA-Py (aries-cloudagent-python) 0.11.x, AnonCreds 1.0, Stratos Blockchain REST API, Python 3.12, httpx, pytest, respx

**Prerequisites:** Part 1 complete. PostgreSQL running. `.env` configured with `STRATOS_API_URL`, `STRATOS_DID_SEED`, and `ISSUER_AGENT_ADMIN_URL`.

**This is Part 2 of 5.**

---

## File Structure

```
services/
└── issuer/
    ├── pyproject.toml
    ├── Dockerfile
    ├── config/
    │   └── acapy-config.yml           # ACA-Py startup flags
    ├── issuer/
    │   ├── __init__.py
    │   ├── stratos_client.py          # Stratos blockchain REST client
    │   ├── did_resolver.py            # ACA-Py did:stratos resolver plugin
    │   ├── schema.py                  # Schema + cred def anchoring
    │   ├── revocation.py              # Revocation registry management
    │   └── bootstrap.py              # One-time setup: anchor schema + cred def
    └── tests/
        ├── conftest.py
        ├── test_stratos_client.py
        ├── test_schema.py
        ├── test_revocation.py
        └── test_e2e_issuance.py
```

**New `.env` variables needed** (add to `.env.example`):
```bash
STRATOS_API_URL=https://stratos-api.thestratos.org/api/v1
STRATOS_API_KEY=change-me
STRATOS_DID_SEED=000000000000000000000000DSTN0001   # 32-char seed for issuer DID
ISSUER_SCHEMA_ID=                                   # set after Task 12 bootstrap
ISSUER_CRED_DEF_ID=                                 # set after Task 12 bootstrap
ISSUER_REV_REG_ID=                                  # set after Task 13 bootstrap
```

---

### Task 9: Issuer Service Scaffold and Stratos Blockchain Client

**Files:**
- Create: `services/issuer/pyproject.toml`
- Create: `services/issuer/issuer/stratos_client.py`
- Test: `services/issuer/tests/test_stratos_client.py`

> **Stratos API note:** The Stratos blockchain exposes a REST API for DID registration, DID resolution, schema anchoring, and revocation registry management. Consult the Stratos SDK docs at `docs/stratos-sdk/` for the exact endpoint paths — the client below uses the expected standard paths and must be updated if the SDK differs.

- [ ] **Step 1: Create `services/issuer/pyproject.toml`**

```toml
[project]
name = "issuer"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "httpx>=0.27.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
test = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "respx>=0.21.0",
]
```

- [ ] **Step 2: Write the failing test**

```python
# services/issuer/tests/conftest.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # services/issuer

# services/issuer/tests/test_stratos_client.py
import pytest
import respx
import httpx
from issuer.stratos_client import StratosClient, DIDDocument

STRATOS_URL = "https://stratos-api.example.org/api/v1"

@pytest.mark.asyncio
@respx.mock
async def test_resolve_did_returns_document():
    test_did = "did:stratos:abc123"
    respx.get(f"{STRATOS_URL}/did/abc123").mock(
        return_value=httpx.Response(200, json={
            "id": test_did,
            "verificationMethod": [{"id": f"{test_did}#key-1", "publicKeyMultibase": "zAbc"}],
        })
    )
    client = StratosClient(api_url=STRATOS_URL, api_key="key")
    doc = await client.resolve_did("did:stratos:abc123")
    assert doc.id == test_did

@pytest.mark.asyncio
@respx.mock
async def test_anchor_schema_returns_schema_id():
    respx.post(f"{STRATOS_URL}/anoncreds/schema").mock(
        return_value=httpx.Response(200, json={"schema_id": "did:stratos:abc123/anoncreds/v0/SCHEMA/GoCSupplier/1.0"})
    )
    client = StratosClient(api_url=STRATOS_URL, api_key="key")
    schema_id = await client.anchor_schema(issuer_did="did:stratos:abc123", name="GoCSupplier", version="1.0", attr_names=["business_number"])
    assert "GoCSupplier" in schema_id
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd services/issuer && python -m pytest tests/test_stratos_client.py -v
```

Expected: `ImportError`

- [ ] **Step 4: Create `services/issuer/issuer/stratos_client.py`**

```python
# services/issuer/issuer/stratos_client.py
import logging
from dataclasses import dataclass, field
import httpx

logger = logging.getLogger(__name__)

@dataclass
class DIDDocument:
    id: str
    verification_method: list[dict] = field(default_factory=list)

class StratosClient:
    """REST client for the Stratos blockchain DID registry and AnonCreds anchoring.

    Endpoint paths follow the expected Stratos REST API convention.
    Update paths if the actual Stratos SDK documentation differs.
    """

    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url.rstrip("/")
        self.headers = {"x-api-key": api_key, "Content-Type": "application/json"}

    def _did_identifier(self, did: str) -> str:
        """Extract the identifier portion from a did:stratos DID."""
        return did.removeprefix("did:stratos:")

    async def resolve_did(self, did: str) -> DIDDocument:
        identifier = self._did_identifier(did)
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{self.api_url}/did/{identifier}", headers=self.headers)
            r.raise_for_status()
            data = r.json()
        return DIDDocument(
            id=data["id"],
            verification_method=data.get("verificationMethod", []),
        )

    async def register_did(self, seed: str) -> str:
        """Register a new DID derived from seed. Returns the did:stratos DID string."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                f"{self.api_url}/did", json={"seed": seed}, headers=self.headers
            )
            r.raise_for_status()
            return r.json()["did"]

    async def anchor_schema(self, issuer_did: str, name: str, version: str, attr_names: list[str]) -> str:
        """Anchor an AnonCreds schema on Stratos. Returns schema_id."""
        payload = {
            "issuer_did": issuer_did,
            "name": name,
            "version": version,
            "attr_names": attr_names,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(f"{self.api_url}/anoncreds/schema", json=payload, headers=self.headers)
            r.raise_for_status()
            return r.json()["schema_id"]

    async def anchor_cred_def(self, issuer_did: str, schema_id: str, tag: str = "default") -> str:
        """Anchor a credential definition. Returns cred_def_id."""
        payload = {"issuer_did": issuer_did, "schema_id": schema_id, "tag": tag, "support_revocation": True}
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(f"{self.api_url}/anoncreds/credential-definition", json=payload, headers=self.headers)
            r.raise_for_status()
            return r.json()["cred_def_id"]

    async def create_revocation_registry(self, cred_def_id: str, max_cred_num: int = 32767) -> str:
        """Create a revocation registry. Returns rev_reg_id."""
        payload = {"cred_def_id": cred_def_id, "max_cred_num": max_cred_num}
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(f"{self.api_url}/anoncreds/revocation-registry", json=payload, headers=self.headers)
            r.raise_for_status()
            return r.json()["rev_reg_id"]

    async def update_revocation_registry(self, rev_reg_id: str, revoked_indices: list[int]) -> None:
        """Publish revocation registry delta for revoked credential indices."""
        payload = {"rev_reg_id": rev_reg_id, "revoked": revoked_indices}
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.patch(f"{self.api_url}/anoncreds/revocation-registry", json=payload, headers=self.headers)
            r.raise_for_status()

    async def get_revocation_status(self, rev_reg_id: str, cred_rev_id: str) -> bool:
        """Returns True if the credential is revoked."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{self.api_url}/anoncreds/revocation-registry/{rev_reg_id}/status",
                params={"cred_rev_id": cred_rev_id},
                headers=self.headers,
            )
            r.raise_for_status()
            return r.json().get("revoked", False)
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd services/issuer && python -m pytest tests/test_stratos_client.py -v
```

Expected: both tests `PASSED`

- [ ] **Step 6: Commit**

```bash
git add services/issuer/
git commit -m "feat: add issuer service scaffold and StratosClient for blockchain operations"
```

---

### Task 10: did:stratos DID Resolver Plugin for ACA-Py

**Files:**
- Create: `services/issuer/issuer/did_resolver.py`
- Test: `services/issuer/tests/test_did_resolver.py`

ACA-Py supports custom DID resolvers via its plugin system. The resolver implements `BaseDIDResolver` from `aries_cloudagent.resolver.base`. When ACA-Py needs to resolve a `did:stratos` DID (to verify a credential definition or schema), it delegates to this plugin.

- [ ] **Step 1: Write the failing test**

```python
# services/issuer/tests/test_did_resolver.py
import pytest
import respx
import httpx
from unittest.mock import AsyncMock, MagicMock
from issuer.did_resolver import StratosDIDResolver

STRATOS_URL = "https://stratos-api.example.org/api/v1"

@pytest.mark.asyncio
@respx.mock
async def test_resolver_supports_did_stratos_method():
    resolver = StratosDIDResolver(api_url=STRATOS_URL, api_key="key")
    assert resolver.supported_did_regex.match("did:stratos:abc123def456")
    assert not resolver.supported_did_regex.match("did:key:zabc")
    assert not resolver.supported_did_regex.match("did:indy:abc")

@pytest.mark.asyncio
@respx.mock
async def test_resolver_returns_did_document():
    test_did = "did:stratos:testidentifier"
    respx.get(f"{STRATOS_URL}/did/testidentifier").mock(
        return_value=httpx.Response(200, json={
            "id": test_did,
            "verificationMethod": [
                {
                    "id": f"{test_did}#key-1",
                    "type": "JsonWebKey2020",
                    "controller": test_did,
                    "publicKeyMultibase": "zSomeBase58Key",
                }
            ],
            "authentication": [f"{test_did}#key-1"],
        })
    )
    resolver = StratosDIDResolver(api_url=STRATOS_URL, api_key="key")
    # resolve() in ACA-Py expects (profile, did) — we test the internal _resolve method
    doc = await resolver._fetch_did_document(test_did)
    assert doc["id"] == test_did
    assert len(doc["verificationMethod"]) == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd services/issuer && python -m pytest tests/test_did_resolver.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Create `services/issuer/issuer/did_resolver.py`**

```python
# services/issuer/issuer/did_resolver.py
import re
import httpx

# ACA-Py base class — imported at runtime when running inside ACA-Py.
# For standalone tests, we provide a minimal stub.
try:
    from aries_cloudagent.resolver.base import BaseDIDResolver, ResolverType
except ImportError:
    class ResolverType:
        NON_NATIVE = "non_native"
    class BaseDIDResolver:
        def __init__(self, type_=None):
            self.type = type_

SUPPORTED_DID_PATTERN = re.compile(r"^did:stratos:[a-zA-Z0-9._-]+$")

class StratosDIDResolver(BaseDIDResolver):
    """ACA-Py DID resolver plugin for the did:stratos method.

    Register in ACA-Py config:
        --plugin issuer.did_resolver
    ACA-Py will call setup() and then resolver.resolve(profile, did) as needed.
    """

    def __init__(self, api_url: str = "", api_key: str = ""):
        super().__init__(ResolverType.NON_NATIVE)
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.supported_did_regex = SUPPORTED_DID_PATTERN

    async def setup(self, context) -> None:
        """Called by ACA-Py on plugin load. Read config from context if needed."""
        settings = context.settings if hasattr(context, "settings") else {}
        self.api_url = settings.get("stratos.api_url", self.api_url)
        self.api_key = settings.get("stratos.api_key", self.api_key)

    async def resolve(self, profile, did: str) -> dict:
        """ACA-Py calls this for any did:stratos DID."""
        return await self._fetch_did_document(did)

    async def _fetch_did_document(self, did: str) -> dict:
        identifier = did.removeprefix("did:stratos:")
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{self.api_url}/did/{identifier}",
                headers={"x-api-key": self.api_key},
            )
            r.raise_for_status()
            return r.json()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd services/issuer && python -m pytest tests/test_did_resolver.py -v
```

Expected: both tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add services/issuer/issuer/did_resolver.py services/issuer/tests/test_did_resolver.py
git commit -m "feat: add did:stratos ACA-Py resolver plugin"
```

---

### Task 11: ACA-Py Agent Configuration and Docker Service

**Files:**
- Create: `services/issuer/config/acapy-config.yml`
- Create: `services/issuer/Dockerfile`
- Modify: `docker-compose.yml` (add `issuer-agent` service)

ACA-Py is run as a container. We configure it to use the Stratos blockchain as its ledger via the custom `did:stratos` resolver plugin. The admin API listens on port 8021 (internal only, not exposed to the internet in production).

- [ ] **Step 1: Create `services/issuer/config/acapy-config.yml`**

```yaml
# services/issuer/config/acapy-config.yml
label: "DSTN Issuer Agent"
wallet-type: askar
wallet-name: dstn-issuer
wallet-key: "${ACAPY_WALLET_KEY}"

# Stratos blockchain as the AnonCreds ledger
genesis-url: "${STRATOS_GENESIS_URL}"
ledger-pool-name: stratos

# DID plugin for did:stratos resolution
plugin:
  - issuer.did_resolver

plugin-config-value:
  - "stratos.api_url=${STRATOS_API_URL}"
  - "stratos.api_key=${STRATOS_API_KEY}"

# Admin API (internal only — do not expose externally)
admin:
  - "0.0.0.0"
  - 8021
admin-insecure-mode: false
admin-api-key: "${ISSUER_AGENT_API_KEY}"

# Inbound/outbound DIDComm — TEE-internal only in production
inbound-transport:
  - - http
    - "0.0.0.0"
    - 8020
outbound-transport:
  - http

auto-provision: true
auto-accept-invites: false
auto-accept-requests: false
log-level: info
```

- [ ] **Step 2: Create `services/issuer/Dockerfile`**

```dockerfile
# services/issuer/Dockerfile
FROM python:3.12-slim

RUN pip install aries-cloudagent==0.11.0

WORKDIR /app
COPY issuer/ ./issuer/
COPY config/ ./config/

ENV PYTHONPATH=/app

CMD ["aca-py", "start", "--arg-file", "config/acapy-config.yml"]
```

- [ ] **Step 3: Add issuer-agent to `docker-compose.yml`**

```yaml
# Add this service block to docker-compose.yml under `services:`
  issuer-agent:
    build:
      context: services/issuer
      dockerfile: Dockerfile
    environment:
      ACAPY_WALLET_KEY: ${ACAPY_WALLET_KEY:-change-wallet-key}
      STRATOS_GENESIS_URL: ${STRATOS_GENESIS_URL}
      STRATOS_API_URL: ${STRATOS_API_URL}
      STRATOS_API_KEY: ${STRATOS_API_KEY}
      ISSUER_AGENT_API_KEY: ${ISSUER_AGENT_API_KEY:-change-me}
    ports:
      - "8020:8020"
      - "8021:8021"
    depends_on:
      - postgres
```

- [ ] **Step 4: Add new env vars to `.env.example`**

```bash
# append to .env.example
ACAPY_WALLET_KEY=change-wallet-key-min-16-chars
STRATOS_GENESIS_URL=https://stratos-api.thestratos.org/genesis
```

- [ ] **Step 5: Build and start the issuer agent**

```bash
docker compose build issuer-agent
docker compose up -d issuer-agent
```

- [ ] **Step 6: Verify agent health**

```bash
curl -H "x-api-key: change-me" http://localhost:8021/status
```

Expected: JSON response with `"ready": true` or similar ACA-Py status payload.

- [ ] **Step 7: Commit**

```bash
git add services/issuer/config/ services/issuer/Dockerfile docker-compose.yml .env.example
git commit -m "feat: configure ACA-Py issuer agent with did:stratos plugin and Docker service"
```

---

### Task 12: AnonCreds Schema and Credential Definition Anchoring

**Files:**
- Create: `services/issuer/issuer/schema.py`
- Create: `services/issuer/issuer/bootstrap.py`
- Test: `services/issuer/tests/test_schema.py`

Run bootstrap once to anchor the schema and cred def on Stratos. The resulting IDs go into `.env` as `ISSUER_SCHEMA_ID` and `ISSUER_CRED_DEF_ID`.

- [ ] **Step 1: Write the failing test**

```python
# services/issuer/tests/test_schema.py
import pytest
import respx
import httpx
from issuer.schema import SchemaManager, DSTN_SCHEMA_ATTRS, DSTN_SCHEMA_NAME, DSTN_SCHEMA_VERSION

STRATOS_URL = "https://stratos-api.example.org/api/v1"
ISSUER_DID = "did:stratos:issuer001"

@pytest.mark.asyncio
@respx.mock
async def test_ensure_schema_anchors_if_not_exists():
    schema_id = f"{ISSUER_DID}/anoncreds/v0/SCHEMA/{DSTN_SCHEMA_NAME}/{DSTN_SCHEMA_VERSION}"
    cred_def_id = f"{ISSUER_DID}/anoncreds/v0/CLAIM_DEF/1/default"
    rev_reg_id = f"{ISSUER_DID}/anoncreds/v0/REV_REG_DEF/1/default/0"

    respx.post(f"{STRATOS_URL}/anoncreds/schema").mock(
        return_value=httpx.Response(200, json={"schema_id": schema_id})
    )
    respx.post(f"{STRATOS_URL}/anoncreds/credential-definition").mock(
        return_value=httpx.Response(200, json={"cred_def_id": cred_def_id})
    )
    respx.post(f"{STRATOS_URL}/anoncreds/revocation-registry").mock(
        return_value=httpx.Response(200, json={"rev_reg_id": rev_reg_id})
    )

    manager = SchemaManager(api_url=STRATOS_URL, api_key="key", issuer_did=ISSUER_DID)
    result = await manager.ensure_schema_and_cred_def()
    assert result["schema_id"] == schema_id
    assert result["cred_def_id"] == cred_def_id
    assert result["rev_reg_id"] == rev_reg_id

def test_dstn_schema_has_required_attributes():
    assert "business_number" in DSTN_SCHEMA_ATTRS
    assert "business_name" in DSTN_SCHEMA_ATTRS
    assert "supplier_status" in DSTN_SCHEMA_ATTRS
    assert "issue_date" in DSTN_SCHEMA_ATTRS
    assert "expiry_date" in DSTN_SCHEMA_ATTRS
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd services/issuer && python -m pytest tests/test_schema.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Create `services/issuer/issuer/schema.py`**

```python
# services/issuer/issuer/schema.py
from issuer.stratos_client import StratosClient

DSTN_SCHEMA_NAME = "GoCSupplierCredential"
DSTN_SCHEMA_VERSION = "1.0"
DSTN_SCHEMA_ATTRS = [
    "business_number",
    "business_name",
    "supplier_status",
    "issue_date",
    "expiry_date",
    "issuing_authority",
]

class SchemaManager:
    def __init__(self, api_url: str, api_key: str, issuer_did: str):
        self.client = StratosClient(api_url=api_url, api_key=api_key)
        self.issuer_did = issuer_did

    async def ensure_schema_and_cred_def(self) -> dict:
        """Idempotent: anchor schema, cred def, and revocation registry if not present.
        Returns dict with schema_id, cred_def_id, rev_reg_id."""
        schema_id = await self.client.anchor_schema(
            issuer_did=self.issuer_did,
            name=DSTN_SCHEMA_NAME,
            version=DSTN_SCHEMA_VERSION,
            attr_names=DSTN_SCHEMA_ATTRS,
        )
        cred_def_id = await self.client.anchor_cred_def(
            issuer_did=self.issuer_did,
            schema_id=schema_id,
            tag="default",
        )
        rev_reg_id = await self.client.create_revocation_registry(
            cred_def_id=cred_def_id,
        )
        return {"schema_id": schema_id, "cred_def_id": cred_def_id, "rev_reg_id": rev_reg_id}
```

- [ ] **Step 4: Create `services/issuer/issuer/bootstrap.py`** (one-time CLI script)

```python
# services/issuer/issuer/bootstrap.py
"""Run once to anchor schema + cred def on Stratos. Outputs IDs to set in .env."""
import asyncio
import os
from issuer.schema import SchemaManager

async def main():
    api_url = os.environ["STRATOS_API_URL"]
    api_key = os.environ["STRATOS_API_KEY"]
    issuer_did = os.environ.get("ISSUER_DID")
    if not issuer_did:
        # Register a new DID from seed if not already set
        from issuer.stratos_client import StratosClient
        seed = os.environ["STRATOS_DID_SEED"]
        client = StratosClient(api_url=api_url, api_key=api_key)
        issuer_did = await client.register_did(seed=seed)
        print(f"ISSUER_DID={issuer_did}")

    manager = SchemaManager(api_url=api_url, api_key=api_key, issuer_did=issuer_did)
    ids = await manager.ensure_schema_and_cred_def()
    print(f"ISSUER_SCHEMA_ID={ids['schema_id']}")
    print(f"ISSUER_CRED_DEF_ID={ids['cred_def_id']}")
    print(f"ISSUER_REV_REG_ID={ids['rev_reg_id']}")
    print("Copy these values into your .env file.")

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd services/issuer && python -m pytest tests/test_schema.py -v
```

Expected: both tests `PASSED`

- [ ] **Step 6: Run bootstrap against real Stratos network**

With the issuer agent running and Stratos API reachable:

```bash
cd services/issuer
STRATOS_API_URL=<url> STRATOS_API_KEY=<key> STRATOS_DID_SEED=<seed> \
    python -m issuer.bootstrap
```

Copy the printed `ISSUER_SCHEMA_ID`, `ISSUER_CRED_DEF_ID`, `ISSUER_REV_REG_ID`, and `ISSUER_DID` values into your `.env`.

- [ ] **Step 7: Commit**

```bash
git add services/issuer/issuer/schema.py services/issuer/issuer/bootstrap.py services/issuer/tests/test_schema.py
git commit -m "feat: AnonCreds schema + cred def anchoring on Stratos; bootstrap script"
```

---

### Task 13: Revocation Registry Management

**Files:**
- Create: `services/issuer/issuer/revocation.py`
- Test: `services/issuer/tests/test_revocation.py`

The `RevocationManager` wraps the Stratos revocation registry operations and persists the cred_rev_id assigned to each credential exchange.

- [ ] **Step 1: Write the failing test**

```python
# services/issuer/tests/test_revocation.py
import pytest
import respx
import httpx
from issuer.revocation import RevocationManager

STRATOS_URL = "https://stratos-api.example.org/api/v1"
REV_REG_ID = "did:stratos:issuer001/anoncreds/v0/REV_REG_DEF/1/default/0"

@pytest.mark.asyncio
@respx.mock
async def test_revoke_by_cred_rev_id_calls_stratos():
    respx.patch(f"{STRATOS_URL}/anoncreds/revocation-registry").mock(
        return_value=httpx.Response(200, json={"result": "ok"})
    )
    manager = RevocationManager(api_url=STRATOS_URL, api_key="key", rev_reg_id=REV_REG_ID)
    success = await manager.revoke(cred_rev_id="5")
    assert success is True

@pytest.mark.asyncio
@respx.mock
async def test_is_revoked_returns_bool():
    respx.get(f"{STRATOS_URL}/anoncreds/revocation-registry/{REV_REG_ID}/status").mock(
        return_value=httpx.Response(200, json={"revoked": True})
    )
    manager = RevocationManager(api_url=STRATOS_URL, api_key="key", rev_reg_id=REV_REG_ID)
    assert await manager.is_revoked(cred_rev_id="5") is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd services/issuer && python -m pytest tests/test_revocation.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Create `services/issuer/issuer/revocation.py`**

```python
# services/issuer/issuer/revocation.py
import logging
from issuer.stratos_client import StratosClient

logger = logging.getLogger(__name__)

class RevocationManager:
    def __init__(self, api_url: str, api_key: str, rev_reg_id: str):
        self.client = StratosClient(api_url=api_url, api_key=api_key)
        self.rev_reg_id = rev_reg_id

    async def revoke(self, cred_rev_id: str) -> bool:
        """Revoke credential at the given index in the revocation registry."""
        try:
            await self.client.update_revocation_registry(
                rev_reg_id=self.rev_reg_id,
                revoked_indices=[int(cred_rev_id)],
            )
            return True
        except Exception as exc:
            logger.error("Revocation failed for cred_rev_id=%s: %s", cred_rev_id, exc)
            return False

    async def is_revoked(self, cred_rev_id: str) -> bool:
        return await self.client.get_revocation_status(self.rev_reg_id, cred_rev_id)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd services/issuer && python -m pytest tests/test_revocation.py -v
```

Expected: both tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add services/issuer/issuer/revocation.py services/issuer/tests/test_revocation.py
git commit -m "feat: add RevocationManager — wraps Stratos revocation registry API"
```

---

### Task 14: Full Credential Trigger Implementation (wires Part 1 stub)

**Files:**
- Modify: `services/das/das/triggers/credential_trigger.py` (fill in schema/cred_def IDs)
- Modify: `shared/config.py` (add schema/cred_def/rev_reg env vars)

The Part 1 stub left `cred_def_id` and `connection_id` empty. Now that we have those IDs from bootstrapping, wire them in. The DIDComm connection between the Issuer TEE and the Holder TEE is established once at startup and reused; the connection_id is resolved by looking up the holder's did:key in ACA-Py's connection records.

- [ ] **Step 1: Add new settings to `shared/config.py`**

```python
# shared/config.py — add these fields to the Settings class
issuer_did: str = ""
issuer_schema_id: str = ""
issuer_cred_def_id: str = ""
issuer_rev_reg_id: str = ""
```

- [ ] **Step 2: Update `das/triggers/credential_trigger.py`** — replace the `issue()` method

```python
# services/das/das/triggers/credential_trigger.py
# Replace the issue() method body with the fully wired version:

async def issue(self, business_number: str, business_name: str, holder_did: str) -> str | None:
    from shared.config import settings
    from datetime import date

    # Resolve ACA-Py connection_id for this holder's did:key
    connection_id = await self._get_or_create_connection(holder_did)
    if not connection_id:
        return None

    payload = {
        "auto_remove": False,
        "connection_id": connection_id,
        "cred_def_id": settings.issuer_cred_def_id,
        "credential_preview": {
            "@type": "issue-credential/2.0/credential-preview",
            "attributes": [
                {"name": "business_number", "value": business_number},
                {"name": "business_name", "value": business_name},
                {"name": "supplier_status", "value": "active"},
                {"name": "issue_date", "value": date.today().isoformat()},
                {"name": "expiry_date", "value": str(date.today().year + 1) + "-01-01"},
                {"name": "issuing_authority", "value": "PSPC / DSTN"},
            ],
        },
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                f"{self.admin_url}/issue-credential-2.0/send",
                json=payload,
                headers=self.headers,
            )
            r.raise_for_status()
            return r.json().get("cred_ex_id")
    except Exception as exc:
        logger.error("Credential issuance failed for %s: %s", business_number, exc)
        return None

async def _get_or_create_connection(self, holder_did: str) -> str | None:
    """Look up ACA-Py connection record for this holder DID. Returns connection_id or None."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{self.admin_url}/connections",
                params={"their_did": holder_did},
                headers=self.headers,
            )
            r.raise_for_status()
            results = r.json().get("results", [])
            if results:
                return results[0]["connection_id"]
            logger.warning("No ACA-Py connection found for holder DID %s", holder_did)
            return None
    except Exception as exc:
        logger.error("Connection lookup failed for %s: %s", holder_did, exc)
        return None
```

- [ ] **Step 3: Update revoke() to use rev_reg_id from settings**

```python
# In CredentialTrigger.revoke(), replace the rev_reg_id="": parameter:
async def revoke(self, cred_ex_id: str, rev_reg_id: str = "") -> bool:
    from shared.config import settings
    actual_rev_reg_id = rev_reg_id or settings.issuer_rev_reg_id
    payload = {"cred_ex_id": cred_ex_id, "rev_reg_id": actual_rev_reg_id, "publish": True}
    # ... rest of method unchanged
```

- [ ] **Step 4: Run the full DAS test suite to ensure no regressions**

```bash
cd services/das && python -m pytest tests/ -v
```

Expected: all tests pass (the trigger tests mock the HTTP calls, so settings defaults are fine).

- [ ] **Step 5: Run the full issuer test suite**

```bash
cd services/issuer && python -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add shared/config.py services/das/das/triggers/credential_trigger.py
git commit -m "feat: wire full CredentialTrigger with cred_def_id, attributes, and revocation registry"
```

---

### Task 15: End-to-End Issuance Integration Test

**Files:**
- Create: `services/issuer/tests/test_e2e_issuance.py`

This test stands up a mock of the ACA-Py admin API and the Stratos API, runs the full sync cycle → status derivation → credential trigger flow, and asserts a credential issuance call was made with the correct attributes.

- [ ] **Step 1: Write and run the integration test**

```python
# services/issuer/tests/test_e2e_issuance.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "services" / "das"))

import pytest
import respx
import httpx
from das.connectors.canadabuys import CanadaBuysConnector
from das.engine.status_derivation import StatusDerivationEngine
from das.triggers.credential_trigger import CredentialTrigger

CANADABUYS_URL = "https://canadabuys.canada.ca/openapi/v1"
ISSUER_URL = "http://issuer:8021"

SAMPLE_CONTRACTS = {"contracts": [{
    "vendor_name": "Acme Corp",
    "business_number": "123456789",
    "contract_date": "2024-01-15",
    "contract_period_end": "2025-01-14",
    "total_value": 200000.0,
    "status": "active",
    "reference_number": "CB-E2E-001",
}]}

@pytest.mark.asyncio
@respx.mock
async def test_full_issuance_flow():
    # Arrange: mock data source
    respx.get(f"{CANADABUYS_URL}/contracts").mock(
        return_value=httpx.Response(200, json=SAMPLE_CONTRACTS)
    )
    # Arrange: mock ACA-Py connection lookup returns a connection
    respx.get(f"{ISSUER_URL}/connections").mock(
        return_value=httpx.Response(200, json={"results": [{"connection_id": "conn-abc"}]})
    )
    # Arrange: mock ACA-Py issuance
    issue_call = respx.post(f"{ISSUER_URL}/issue-credential-2.0/send").mock(
        return_value=httpx.Response(200, json={"cred_ex_id": "cred-e2e-001"})
    )

    # Act
    connector = CanadaBuysConnector(base_url=CANADABUYS_URL)
    records = await connector.fetch_contracts()
    engine = StatusDerivationEngine()
    derived = engine.derive(records)

    trigger = CredentialTrigger(admin_url=ISSUER_URL, api_key="test")
    for status in derived.values():
        if status.status == "active":
            cred_ex_id = await trigger.issue(
                business_number=status.business_number,
                business_name=status.business_name,
                holder_did="did:key:zTestHolder",
            )

    # Assert
    assert issue_call.called
    assert cred_ex_id == "cred-e2e-001"
    request_body = issue_call.calls[0].request.content
    import json
    body = json.loads(request_body)
    attrs = {a["name"]: a["value"] for a in body["credential_preview"]["attributes"]}
    assert attrs["business_number"] == "123456789"
    assert attrs["supplier_status"] == "active"
```

- [ ] **Step 2: Run the test**

```bash
cd services/issuer && python -m pytest tests/test_e2e_issuance.py -v
```

Expected: `PASSED`

- [ ] **Step 3: Commit**

```bash
git add services/issuer/tests/test_e2e_issuance.py
git commit -m "test: end-to-end issuance flow — data ingestion to ACA-Py credential offer"
```

---

## Part 2 Complete

Run full test suites:

```bash
cd services/das && python -m pytest tests/ -v
cd services/issuer && python -m pytest tests/ -v
```

Expected: all tests green.

**What's working after Part 2:**
- ACA-Py issuer agent running in Docker with did:stratos resolver plugin
- AnonCreds schema and credential definition anchored on Stratos Blockchain
- Revocation registry live on Stratos Decentralized Storage
- Credential Trigger fully wired: DAS issues credentials via ACA-Py admin API
- End-to-end issuance flow tested with mocks

**Part 3 will:** implement WebAuthn passkey registration, the Passkey Registry (pubkey → biz# → did:key), the TEE Holder Agent (session-scoped ACA-Py holder instance), and the Credential Store (encrypted at rest).
