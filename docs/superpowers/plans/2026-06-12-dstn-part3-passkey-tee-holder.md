# DSTN Part 3: Passkey Registry and TEE Holder Agent

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Supplier Portal backend — WebAuthn passkey registration and authentication, the Passkey Registry (P-256 pubkey → business_number → did:key), did:key derivation, the TEE Holder Agent (session-scoped credential decryption), and the Credential Store (AES-256-GCM encrypted at rest).

**Architecture:** A FastAPI service (`services/portal/`) handles all supplier-facing API endpoints. WebAuthn uses `py_webauthn` for challenge generation and assertion verification. Credentials issued by the Aries Issuer Agent are delivered to the portal's `/holder/receive` endpoint, encrypted with AES-256-GCM, and stored in PostgreSQL. On each passkey-authenticated session, the credential is decrypted in-memory. In Part 5, the encryption key moves from a server-derived HKDF key to a TEE hardware key.

**Tech Stack:** Python 3.12, FastAPI, py-webauthn 2.x, cryptography (pyca), pyjwt, SQLAlchemy 2, base58, cbor2, pytest, httpx

**Prerequisites:** Parts 1 and 2 complete. PostgreSQL running. ACA-Py issuer agent configured and bootstrap done (ISSUER_DID, ISSUER_CRED_DEF_ID known).

**This is Part 3 of 5.**

---

## File Structure

```
services/
└── portal/
    ├── pyproject.toml
    ├── portal/
    │   ├── __init__.py
    │   ├── main.py                  # FastAPI app, routes
    │   ├── passkey.py               # WebAuthn challenge generation + verification
    │   ├── passkey_registry.py      # DB ops: store/lookup passkey credential records
    │   ├── did_key.py               # did:key derivation from COSE P-256 public key
    │   ├── holder_agent.py          # TEE Holder Agent: activate/deactivate session
    │   ├── credential_store.py      # AES-256-GCM encrypt/decrypt credential at rest
    │   └── session.py               # JWT session token (business_number + did:key)
    └── tests/
        ├── conftest.py
        ├── test_did_key.py
        ├── test_passkey.py
        ├── test_credential_store.py
        ├── test_holder_agent.py
        └── test_session_flow.py
```

**New ORM model** (add to `shared/models.py`):

```python
class PasskeyRecord(Base):
    __tablename__ = "passkey_records"
    credential_id: Mapped[bytes] = mapped_column(LargeBinary, primary_key=True)
    business_number: Mapped[str] = mapped_column(String(15), index=True)
    public_key_cose: Mapped[bytes] = mapped_column(LargeBinary)  # raw COSE bytes from WebAuthn
    did_key: Mapped[str] = mapped_column(String(512), unique=True)
    sign_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class EncryptedCredential(Base):
    __tablename__ = "encrypted_credentials"
    did_key: Mapped[str] = mapped_column(String(512), primary_key=True)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary)     # AES-256-GCM ciphertext
    nonce: Mapped[bytes] = mapped_column(LargeBinary)          # 12-byte GCM nonce
    cred_ex_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

**New `.env` variables** (add to `.env.example`):
```bash
PORTAL_SECRET_KEY=change-me-32-chars-minimum
PORTAL_RP_ID=localhost                    # WebAuthn relying party ID (domain in prod)
PORTAL_RP_NAME=DSTN Supplier Portal
PORTAL_ORIGIN=http://localhost:3000       # frontend origin
```

---

### Task 16: Portal Service Scaffold and Shared Models

**Files:**
- Create: `services/portal/pyproject.toml`
- Modify: `shared/models.py` (add `PasskeyRecord`, `EncryptedCredential`)
- Run Alembic migration

- [ ] **Step 1: Create `services/portal/pyproject.toml`**

```toml
[project]
name = "portal"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.30.0",
    "py-webauthn>=2.1.0",
    "cryptography>=42.0.0",
    "pyjwt[crypto]>=2.8.0",
    "base58>=2.1.1",
    "cbor2>=5.6.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.29.0",
    "httpx>=0.27.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
test = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.27.0",
    "aiosqlite>=0.20.0",
]
```

- [ ] **Step 2: Add `PasskeyRecord` and `EncryptedCredential` to `shared/models.py`**

```python
# shared/models.py — append these two classes (after existing imports)
from sqlalchemy import LargeBinary, Integer

class PasskeyRecord(Base):
    __tablename__ = "passkey_records"
    credential_id: Mapped[bytes] = mapped_column(LargeBinary, primary_key=True)
    business_number: Mapped[str] = mapped_column(String(15), index=True)
    public_key_cose: Mapped[bytes] = mapped_column(LargeBinary)
    did_key: Mapped[str] = mapped_column(String(512), unique=True)
    sign_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class EncryptedCredential(Base):
    __tablename__ = "encrypted_credentials"
    did_key: Mapped[str] = mapped_column(String(512), primary_key=True)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
    nonce: Mapped[bytes] = mapped_column(LargeBinary)
    cred_ex_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 3: Generate and apply Alembic migration**

```bash
alembic revision --autogenerate -m "add passkey_records and encrypted_credentials tables"
alembic upgrade head
```

Expected: migration runs cleanly, both new tables exist in PostgreSQL.

- [ ] **Step 4: Commit**

```bash
git add services/portal/ shared/models.py alembic/
git commit -m "feat: portal service scaffold; add PasskeyRecord and EncryptedCredential models"
```

---

### Task 17: did:key Derivation from P-256 Public Key

**Files:**
- Create: `services/portal/portal/did_key.py`
- Create: `services/portal/tests/conftest.py`
- Test: `services/portal/tests/test_did_key.py`

The supplier's holder DID is derived deterministically from the WebAuthn P-256 public key. The COSE-encoded public key from `py_webauthn` is decoded to extract the compressed P-256 point, then encoded as a `did:key` using multicodec + base58btc.

- [ ] **Step 1: Write the failing test**

```python
# services/portal/tests/conftest.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))   # repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # services/portal

# services/portal/tests/test_did_key.py
import pytest
import base64
from portal.did_key import derive_did_key_from_cose

# Minimal valid COSE_Key for P-256 (kty=2, crv=1, x=32bytes, y=32bytes)
# kty=2 (EC2), crv=1 (P-256), x=b'\x01'*32, y=b'\x02'*32
# CBOR-encoded:
import cbor2
COSE_KEY = cbor2.dumps({
    1: 2,           # kty: EC2
    3: -7,          # alg: ES256
    -1: 1,          # crv: P-256
    -2: b"\x01" * 32,  # x coordinate
    -3: b"\x02" * 32,  # y coordinate
})

def test_derive_did_key_starts_with_prefix():
    did = derive_did_key_from_cose(COSE_KEY)
    assert did.startswith("did:key:z")

def test_derive_did_key_is_deterministic():
    did1 = derive_did_key_from_cose(COSE_KEY)
    did2 = derive_did_key_from_cose(COSE_KEY)
    assert did1 == did2

def test_derive_did_key_different_keys_different_dids():
    cose2 = cbor2.dumps({1: 2, 3: -7, -1: 1, -2: b"\x03" * 32, -3: b"\x04" * 32})
    did1 = derive_did_key_from_cose(COSE_KEY)
    did2 = derive_did_key_from_cose(cose2)
    assert did1 != did2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd services/portal && python -m pytest tests/test_did_key.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Create `services/portal/portal/did_key.py`**

```python
# services/portal/portal/did_key.py
import cbor2
import base58

# P-256 (secp256r1) multicodec prefix: varint(0x1200) = [0x80, 0x24]
_P256_MULTICODEC = bytes([0x80, 0x24])

def derive_did_key_from_cose(cose_bytes: bytes) -> str:
    """Derive did:key from a COSE_Key-encoded P-256 public key.

    Algorithm:
    1. Decode COSE map to get x and y coordinates (32 bytes each)
    2. Form compressed point: 0x02|0x03 prefix + x (33 bytes)
    3. Prepend P-256 multicodec prefix [0x80, 0x24]
    4. Base58btc encode, prefix with 'z'
    """
    cose = cbor2.loads(cose_bytes)
    x: bytes = cose[-2]  # COSE -2 = x
    y: bytes = cose[-3]  # COSE -3 = y

    # SEC1 compressed point: 0x02 if y is even, 0x03 if odd
    prefix = 0x02 if y[-1] % 2 == 0 else 0x03
    compressed = bytes([prefix]) + x

    multicodec_key = _P256_MULTICODEC + compressed
    encoded = base58.b58encode(multicodec_key).decode()
    return f"did:key:z{encoded}"
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd services/portal && python -m pytest tests/test_did_key.py -v
```

Expected: all 3 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add services/portal/portal/did_key.py services/portal/tests/
git commit -m "feat: did:key derivation from WebAuthn COSE P-256 public key"
```

---

### Task 18: WebAuthn Passkey Registration and Authentication

**Files:**
- Create: `services/portal/portal/passkey.py`
- Create: `services/portal/portal/passkey_registry.py`
- Test: `services/portal/tests/test_passkey.py`

`passkey.py` wraps `py_webauthn` challenge generation and response verification. `passkey_registry.py` does the DB operations. Challenges are stored in an in-memory dict (sufficient for single-instance dev; replace with Redis in production).

- [ ] **Step 1: Write the failing test**

```python
# services/portal/tests/test_passkey.py
import pytest
from unittest.mock import MagicMock, patch
from portal.passkey import PasskeyManager

def test_begin_registration_returns_options_and_challenge():
    manager = PasskeyManager(rp_id="localhost", rp_name="DSTN", origin="http://localhost:3000")
    options, challenge = manager.begin_registration(business_number="123456789", user_display_name="Acme Corp")
    assert options is not None
    assert len(challenge) > 0

def test_begin_authentication_returns_options_and_challenge():
    manager = PasskeyManager(rp_id="localhost", rp_name="DSTN", origin="http://localhost:3000")
    options, challenge = manager.begin_authentication()
    assert options is not None
    assert len(challenge) > 0

def test_challenge_stored_after_begin_registration():
    manager = PasskeyManager(rp_id="localhost", rp_name="DSTN", origin="http://localhost:3000")
    _, challenge = manager.begin_registration("999888777", "Test Corp")
    assert manager.has_pending_challenge(challenge)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd services/portal && python -m pytest tests/test_passkey.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Create `services/portal/portal/passkey.py`**

```python
# services/portal/portal/passkey.py
import base64
import secrets
from webauthn import generate_registration_options, generate_authentication_options
from webauthn.helpers.structs import (
    PublicKeyCredentialDescriptor,
    AuthenticatorSelectionCriteria,
    UserVerificationRequirement,
    ResidentKeyRequirement,
)
from webauthn.helpers import bytes_to_base64url

_PENDING_CHALLENGES: dict[str, str] = {}  # challenge_b64 → business_number ("" for auth)

class PasskeyManager:
    def __init__(self, rp_id: str, rp_name: str, origin: str):
        self.rp_id = rp_id
        self.rp_name = rp_name
        self.origin = origin

    def begin_registration(self, business_number: str, user_display_name: str) -> tuple[object, str]:
        options = generate_registration_options(
            rp_id=self.rp_id,
            rp_name=self.rp_name,
            user_id=business_number.encode(),
            user_name=business_number,
            user_display_name=user_display_name,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.REQUIRED,
            ),
        )
        challenge_b64 = bytes_to_base64url(options.challenge)
        _PENDING_CHALLENGES[challenge_b64] = business_number
        return options, challenge_b64

    def begin_authentication(self) -> tuple[object, str]:
        options = generate_authentication_options(
            rp_id=self.rp_id,
            user_verification=UserVerificationRequirement.REQUIRED,
        )
        challenge_b64 = bytes_to_base64url(options.challenge)
        _PENDING_CHALLENGES[challenge_b64] = ""
        return options, challenge_b64

    def consume_challenge(self, challenge_b64: str) -> str | None:
        """Returns the associated business_number and removes the challenge (one-time use)."""
        return _PENDING_CHALLENGES.pop(challenge_b64, None)

    def has_pending_challenge(self, challenge_b64: str) -> bool:
        return challenge_b64 in _PENDING_CHALLENGES
```

- [ ] **Step 4: Create `services/portal/portal/passkey_registry.py`**

```python
# services/portal/portal/passkey_registry.py
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from shared.models import PasskeyRecord, SupplierRecord, SupplierStatus
from portal.did_key import derive_did_key_from_cose
import json
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class PasskeyRegistry:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def register(self, business_number: str, credential_id: bytes, public_key_cose: bytes, sign_count: int) -> str:
        """Store passkey registration. Returns the derived did:key."""
        did_key = derive_did_key_from_cose(public_key_cose)

        existing = await self.session.get(PasskeyRecord, credential_id)
        if existing:
            existing.sign_count = sign_count
        else:
            record = PasskeyRecord(
                credential_id=credential_id,
                business_number=business_number,
                public_key_cose=public_key_cose,
                did_key=did_key,
                sign_count=sign_count,
            )
            self.session.add(record)

        # Update supplier_records with did_key and promote status if data pipeline already found them
        supplier = await self.session.get(SupplierRecord, business_number)
        if supplier:
            supplier.did_key = did_key
            if supplier.status == SupplierStatus.PENDING_REGISTRATION:
                supplier.status = SupplierStatus.ACTIVE  # DAS will trigger issuance on next cycle
        await self.session.commit()
        return did_key

    async def lookup_by_credential_id(self, credential_id: bytes) -> PasskeyRecord | None:
        return await self.session.get(PasskeyRecord, credential_id)

    async def update_sign_count(self, credential_id: bytes, new_sign_count: int) -> None:
        record = await self.session.get(PasskeyRecord, credential_id)
        if record:
            record.sign_count = new_sign_count
            await self.session.commit()
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd services/portal && python -m pytest tests/test_passkey.py -v
```

Expected: all 3 tests `PASSED`

- [ ] **Step 6: Commit**

```bash
git add services/portal/portal/passkey.py services/portal/portal/passkey_registry.py services/portal/tests/test_passkey.py
git commit -m "feat: WebAuthn passkey manager and registry — registration flow with did:key derivation"
```

---

### Task 19: Credential Store (AES-256-GCM Encryption at Rest)

**Files:**
- Create: `services/portal/portal/credential_store.py`
- Test: `services/portal/tests/test_credential_store.py`

The Credential Store encrypts AnonCreds credential JSON with AES-256-GCM before persisting to PostgreSQL. The encryption key is derived via HKDF(server_secret + did:key). In Part 5 this key derivation moves inside the TEE.

- [ ] **Step 1: Write the failing test**

```python
# services/portal/tests/test_credential_store.py
import pytest
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from shared.models import Base, EncryptedCredential
from portal.credential_store import CredentialStore

SAMPLE_CREDENTIAL = {
    "schema_id": "did:stratos:issuer/schema/GoCSupplier/1.0",
    "cred_def_id": "did:stratos:issuer/cred_def/1/default",
    "values": {"business_number": "123456789", "supplier_status": "active"},
}
SERVER_SECRET = "test-server-secret-32-chars-!!!"
DID_KEY = "did:key:zTestDID"

@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s

async def test_store_and_retrieve_credential(session):
    store = CredentialStore(session, server_secret=SERVER_SECRET)
    cred_json = json.dumps(SAMPLE_CREDENTIAL)
    await store.store(did_key=DID_KEY, credential_json=cred_json, cred_ex_id="cred-001")
    retrieved = await store.retrieve(did_key=DID_KEY)
    assert retrieved is not None
    assert json.loads(retrieved)["values"]["business_number"] == "123456789"

async def test_retrieve_nonexistent_returns_none(session):
    store = CredentialStore(session, server_secret=SERVER_SECRET)
    result = await store.retrieve(did_key="did:key:zNonExistent")
    assert result is None

async def test_encryption_produces_different_ciphertext_each_call(session):
    store = CredentialStore(session, server_secret=SERVER_SECRET)
    cred_json = json.dumps(SAMPLE_CREDENTIAL)
    await store.store(did_key=DID_KEY, credential_json=cred_json)
    rec = await session.get(EncryptedCredential, DID_KEY)
    # Ciphertext should not equal plaintext
    assert rec.ciphertext != cred_json.encode()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd services/portal && python -m pytest tests/test_credential_store.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Create `services/portal/portal/credential_store.py`**

```python
# services/portal/portal/credential_store.py
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.hashes import SHA256
from sqlalchemy.ext.asyncio import AsyncSession
from shared.models import EncryptedCredential
from datetime import datetime, timezone

class CredentialStore:
    def __init__(self, session: AsyncSession, server_secret: str):
        self.session = session
        self._server_secret = server_secret.encode()

    def _derive_key(self, did_key: str) -> bytes:
        """Derive a 32-byte AES key from server_secret + did_key using HKDF."""
        hkdf = HKDF(algorithm=SHA256(), length=32, salt=None, info=did_key.encode())
        return hkdf.derive(self._server_secret)

    def _encrypt(self, did_key: str, plaintext: bytes) -> tuple[bytes, bytes]:
        key = self._derive_key(did_key)
        nonce = os.urandom(12)  # 96-bit GCM nonce
        ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)
        return ciphertext, nonce

    def _decrypt(self, did_key: str, ciphertext: bytes, nonce: bytes) -> bytes:
        key = self._derive_key(did_key)
        return AESGCM(key).decrypt(nonce, ciphertext, None)

    async def store(self, did_key: str, credential_json: str, cred_ex_id: str | None = None) -> None:
        ciphertext, nonce = self._encrypt(did_key, credential_json.encode())
        existing = await self.session.get(EncryptedCredential, did_key)
        now = datetime.now(timezone.utc)
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
        """Returns decrypted credential JSON, or None if not found."""
        record = await self.session.get(EncryptedCredential, did_key)
        if not record:
            return None
        plaintext = self._decrypt(did_key, record.ciphertext, record.nonce)
        return plaintext.decode()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd services/portal && python -m pytest tests/test_credential_store.py -v
```

Expected: all 3 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add services/portal/portal/credential_store.py services/portal/tests/test_credential_store.py
git commit -m "feat: AES-256-GCM credential store with HKDF key derivation per did:key"
```

---

### Task 20: TEE Holder Agent (Session-Scoped Activation)

**Files:**
- Create: `services/portal/portal/holder_agent.py`
- Test: `services/portal/tests/test_holder_agent.py`

The Holder Agent activates when a supplier authenticates with their passkey. It decrypts the credential into memory, makes it available for the session, then clears all key material on deactivation. In production (Part 5), this runs inside the Stratos TEE; in development, it runs as an in-memory session object.

- [ ] **Step 1: Write the failing test**

```python
# services/portal/tests/test_holder_agent.py
import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from portal.holder_agent import HolderSession

SAMPLE_CRED_JSON = json.dumps({
    "business_number": "123456789",
    "business_name": "Acme Corp",
    "supplier_status": "active",
    "issue_date": "2026-01-01",
    "expiry_date": "2027-01-01",
    "issuing_authority": "PSPC / DSTN",
})

async def test_activate_loads_credential():
    mock_store = MagicMock()
    mock_store.retrieve = AsyncMock(return_value=SAMPLE_CRED_JSON)
    session = HolderSession(did_key="did:key:zTest", credential_store=mock_store)
    await session.activate()
    assert session.is_active
    cred = session.get_credential()
    assert cred["business_number"] == "123456789"
    assert cred["supplier_status"] == "active"

async def test_deactivate_clears_credential():
    mock_store = MagicMock()
    mock_store.retrieve = AsyncMock(return_value=SAMPLE_CRED_JSON)
    session = HolderSession(did_key="did:key:zTest", credential_store=mock_store)
    await session.activate()
    session.deactivate()
    assert not session.is_active
    assert session.get_credential() is None

async def test_activate_with_no_credential_stays_inactive():
    mock_store = MagicMock()
    mock_store.retrieve = AsyncMock(return_value=None)
    session = HolderSession(did_key="did:key:zNoCred", credential_store=mock_store)
    await session.activate()
    assert not session.is_active
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd services/portal && python -m pytest tests/test_holder_agent.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Create `services/portal/portal/holder_agent.py`**

```python
# services/portal/portal/holder_agent.py
import json
import logging
from portal.credential_store import CredentialStore

logger = logging.getLogger(__name__)

class HolderSession:
    """Session-scoped holder agent. Activate on passkey authentication, deactivate at session end.

    In production (Part 5): wrap this class to run inside Stratos TEE, deriving the
    decryption key from hardware-attested TEE state rather than the HKDF server secret.
    The interface (activate / deactivate / get_credential) stays identical.
    """

    def __init__(self, did_key: str, credential_store: CredentialStore):
        self.did_key = did_key
        self._store = credential_store
        self._credential: dict | None = None

    @property
    def is_active(self) -> bool:
        return self._credential is not None

    async def activate(self) -> None:
        """Decrypt and load credential into memory. No-op if no credential is stored."""
        cred_json = await self._store.retrieve(self.did_key)
        if cred_json is None:
            logger.info("No stored credential for %s — session inactive", self.did_key)
            return
        self._credential = json.loads(cred_json)

    def deactivate(self) -> None:
        """Clear all in-memory key material. Must be called at session end."""
        self._credential = None
        logger.info("Holder session deactivated for %s — key material cleared", self.did_key)

    def get_credential(self) -> dict | None:
        """Returns the in-memory credential dict, or None if session is not active."""
        return self._credential
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd services/portal && python -m pytest tests/test_holder_agent.py -v
```

Expected: all 3 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add services/portal/portal/holder_agent.py services/portal/tests/test_holder_agent.py
git commit -m "feat: TEE Holder Agent — session-scoped credential activation and deactivation"
```

---

### Task 21: Session JWT and Portal FastAPI Application

**Files:**
- Create: `services/portal/portal/session.py`
- Create: `services/portal/portal/main.py`
- Test: `services/portal/tests/test_session_flow.py`

The portal backend exposes five endpoints. The session JWT is issued after successful passkey authentication and must accompany all subsequent portal API calls.

Endpoints:
- `GET  /passkey/register/begin?business_number=<bn>` → WebAuthn registration options
- `POST /passkey/register/complete` → verify + store passkey, return session JWT
- `GET  /passkey/auth/begin` → WebAuthn authentication options
- `POST /passkey/auth/complete` → verify + return session JWT
- `GET  /credential/status` (requires JWT) → return credential status from holder session
- `POST /holder/receive` (called by Issuer Agent after issuance) → store credential

- [ ] **Step 1: Create `services/portal/portal/session.py`**

```python
# services/portal/portal/session.py
import jwt
from datetime import datetime, timezone, timedelta

SESSION_EXPIRY_HOURS = 8

def create_session_token(business_number: str, did_key: str, secret: str) -> str:
    payload = {
        "sub": business_number,
        "did_key": did_key,
        "exp": datetime.now(timezone.utc) + timedelta(hours=SESSION_EXPIRY_HOURS),
    }
    return jwt.encode(payload, secret, algorithm="HS256")

def decode_session_token(token: str, secret: str) -> dict:
    return jwt.decode(token, secret, algorithms=["HS256"])
```

- [ ] **Step 2: Create `services/portal/portal/main.py`**

```python
# services/portal/portal/main.py
import json
import logging
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from shared.config import settings
from shared.db import async_session_factory
from portal.passkey import PasskeyManager
from portal.passkey_registry import PasskeyRegistry
from portal.credential_store import CredentialStore
from portal.holder_agent import HolderSession
from portal.session import create_session_token, decode_session_token
from webauthn import verify_registration_response, verify_authentication_response
from webauthn.helpers.structs import AuthenticatorTransport

app = FastAPI(title="DSTN Supplier Portal")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
_passkey_mgr = PasskeyManager(rp_id=settings.portal_rp_id, rp_name=settings.portal_rp_name, origin=settings.portal_origin)

class RegistrationCompleteRequest(BaseModel):
    challenge: str
    credential: dict   # raw PublicKeyCredential JSON from browser

class AuthCompleteRequest(BaseModel):
    challenge: str
    assertion: dict    # raw authentication assertion JSON from browser

class HolderReceiveRequest(BaseModel):
    did_key: str
    credential_json: str
    cred_ex_id: str | None = None

def _require_session(authorization: str = Header(...)) -> dict:
    try:
        token = authorization.removeprefix("Bearer ")
        return decode_session_token(token, settings.portal_secret_key)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

@app.get("/passkey/register/begin")
async def register_begin(business_number: str):
    options, challenge = _passkey_mgr.begin_registration(business_number, business_number)
    return {"options": options.model_dump() if hasattr(options, "model_dump") else options.__dict__, "challenge": challenge}

@app.post("/passkey/register/complete")
async def register_complete(body: RegistrationCompleteRequest):
    business_number = _passkey_mgr.consume_challenge(body.challenge)
    if business_number is None:
        raise HTTPException(400, "Invalid or expired challenge")
    try:
        verification = verify_registration_response(
            credential=body.credential,
            expected_challenge=body.challenge.encode(),
            expected_rp_id=settings.portal_rp_id,
            expected_origin=settings.portal_origin,
        )
    except Exception as exc:
        raise HTTPException(400, f"Registration verification failed: {exc}")
    async with async_session_factory() as session:
        registry = PasskeyRegistry(session)
        did_key = await registry.register(
            business_number=business_number,
            credential_id=verification.credential_id,
            public_key_cose=verification.credential_public_key,
            sign_count=verification.sign_count,
        )
    token = create_session_token(business_number, did_key, settings.portal_secret_key)
    return {"session_token": token, "did_key": did_key}

@app.get("/passkey/auth/begin")
async def auth_begin():
    options, challenge = _passkey_mgr.begin_authentication()
    return {"options": options.model_dump() if hasattr(options, "model_dump") else options.__dict__, "challenge": challenge}

@app.post("/passkey/auth/complete")
async def auth_complete(body: AuthCompleteRequest):
    _passkey_mgr.consume_challenge(body.challenge)
    credential_id_bytes = bytes(body.assertion.get("rawId", []))
    async with async_session_factory() as session:
        registry = PasskeyRegistry(session)
        passkey_record = await registry.lookup_by_credential_id(credential_id_bytes)
        if passkey_record is None:
            raise HTTPException(401, "Passkey not registered")
        try:
            verification = verify_authentication_response(
                credential=body.assertion,
                expected_challenge=body.challenge.encode(),
                expected_rp_id=settings.portal_rp_id,
                expected_origin=settings.portal_origin,
                credential_public_key=passkey_record.public_key_cose,
                credential_current_sign_count=passkey_record.sign_count,
            )
        except Exception as exc:
            raise HTTPException(401, f"Authentication failed: {exc}")
        await registry.update_sign_count(credential_id_bytes, verification.new_sign_count)
        token = create_session_token(passkey_record.business_number, passkey_record.did_key, settings.portal_secret_key)
    return {"session_token": token, "did_key": passkey_record.did_key}

@app.get("/credential/status")
async def credential_status(session_data: dict = Depends(_require_session)):
    did_key = session_data["did_key"]
    async with async_session_factory() as db_session:
        store = CredentialStore(db_session, settings.portal_secret_key)
        holder = HolderSession(did_key, store)
        await holder.activate()
        cred = holder.get_credential()
        holder.deactivate()
    if cred is None:
        return {"status": "pending", "did_key": did_key}
    return {"status": cred.get("supplier_status", "unknown"), "credential": cred, "did_key": did_key}

@app.post("/holder/receive")
async def holder_receive(body: HolderReceiveRequest):
    """Called by the Aries Issuer Agent after credential issuance."""
    async with async_session_factory() as db_session:
        store = CredentialStore(db_session, settings.portal_secret_key)
        await store.store(body.did_key, body.credential_json, body.cred_ex_id)
    return {"result": "stored"}
```

- [ ] **Step 3: Add portal settings to `shared/config.py`**

```python
# shared/config.py — add to Settings class
portal_secret_key: str = "change-me-32-chars-minimum"
portal_rp_id: str = "localhost"
portal_rp_name: str = "DSTN Supplier Portal"
portal_origin: str = "http://localhost:3000"
```

- [ ] **Step 4: Write a session flow integration test**

```python
# services/portal/tests/test_session_flow.py
import json
import pytest
from portal.session import create_session_token, decode_session_token

SECRET = "test-secret-32-chars-exactly!!!!"

def test_create_and_decode_session_token():
    token = create_session_token("123456789", "did:key:zTest", SECRET)
    payload = decode_session_token(token, SECRET)
    assert payload["sub"] == "123456789"
    assert payload["did_key"] == "did:key:zTest"

def test_decode_invalid_token_raises():
    import pytest, jwt
    with pytest.raises(Exception):
        decode_session_token("not-a-token", SECRET)
```

- [ ] **Step 5: Run all portal tests**

```bash
cd services/portal && python -m pytest tests/ -v
```

Expected: all tests `PASSED`

- [ ] **Step 6: Start the portal service and verify it responds**

```bash
cd services/portal && uvicorn portal.main:app --port 8030 --reload
```

In a second terminal:

```bash
curl http://localhost:8030/passkey/register/begin?business_number=123456789
```

Expected: JSON response with `options` and `challenge` fields.

- [ ] **Step 7: Commit**

```bash
git add services/portal/portal/ services/portal/tests/test_session_flow.py shared/config.py
git commit -m "feat: portal FastAPI app — passkey registration/auth, holder session, credential receive endpoint"
```

---

## Part 3 Complete

Run the full test suite:

```bash
cd services/portal && python -m pytest tests/ -v
cd services/das && python -m pytest tests/ -v
cd services/issuer && python -m pytest tests/ -v
```

Expected: all tests green.

**What's working after Part 3:**
- Supplier portal backend running on port 8030
- WebAuthn passkey registration and authentication (py_webauthn)
- P-256 COSE key → did:key derivation
- Passkey Registry persisting pubkey → biz# → did:key in PostgreSQL
- AES-256-GCM Credential Store with HKDF key derivation
- TEE Holder Agent: activate (decrypt), get_credential, deactivate (clear)
- Session JWT issued after passkey authentication
- `/holder/receive` endpoint for Issuer Agent to deliver credentials post-issuance

**Part 4 will:** build the public Verification API, the React Supplier Portal frontend (WebAuthn JS, credential status view, embed snippet generator), the embeddable Verifier Widget, bilingual EN/FR UI, and the Admin Dashboard.
