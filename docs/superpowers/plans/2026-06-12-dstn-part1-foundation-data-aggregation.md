# DSTN Part 1: Foundation & Data Aggregation Service

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the project repo, database layer, and complete Data Aggregation Service (CanadaBuys + Open Gov connectors, Status Derivation Engine, Pending State Store, Credential Trigger stub, and scheduled sync runner).

**Architecture:** Python 3.12 monorepo. Each service lives under `services/`. Shared SQLAlchemy models and config live under `shared/`. The DAS runs as a long-lived process with APScheduler; it writes supplier status to PostgreSQL and emits trigger events to the Issuer Agent (stubbed in this part, wired in Part 2).

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL 16, APScheduler 3.x, httpx, pydantic 2.x, pytest, respx (HTTP mocking)

**This is Part 1 of 5.** Parts 2–5 implement the Credential Protocol Layer, Passkey/TEE Holder, Supplier Portal/Verification API, and Hardening/Deployment respectively.

---

## File Structure

```
trustcan/
├── docker-compose.yml
├── pyproject.toml                     # root workspace (uv workspaces)
├── .env.example
├── alembic/
│   ├── alembic.ini
│   ├── env.py
│   └── versions/
├── shared/
│   ├── __init__.py
│   ├── config.py                      # env-var config (pydantic-settings)
│   ├── db.py                          # SQLAlchemy engine + session factory
│   └── models.py                      # SupplierRecord, AuditEvent ORM models
└── services/
    └── das/                           # Data Aggregation Service
        ├── pyproject.toml
        ├── das/
        │   ├── __init__.py
        │   ├── main.py                # entrypoint: starts scheduler
        │   ├── scheduler.py           # APScheduler job definitions
        │   ├── connectors/
        │   │   ├── __init__.py
        │   │   ├── base.py            # Connector abstract base class
        │   │   ├── canadabuys.py      # CanadaBuys connector
        │   │   ├── open_gov.py        # Open Government connector
        │   │   └── future_auth.py     # Pluggable stub for future source
        │   ├── engine/
        │   │   ├── __init__.py
        │   │   ├── status_derivation.py  # Status logic: awarded + good standing
        │   │   └── pending_state.py      # Mark supplier pending_registration
        │   └── triggers/
        │       ├── __init__.py
        │       └── credential_trigger.py # Stub: calls Issuer Agent API (wired in Part 2)
        └── tests/
            ├── conftest.py
            ├── test_canadabuys.py
            ├── test_open_gov.py
            ├── test_status_derivation.py
            ├── test_pending_state.py
            └── test_credential_trigger.py
```

---

### Task 1: Repo Scaffold and Dev Environment

**Files:**
- Create: `pyproject.toml` (root)
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `services/das/pyproject.toml`

- [ ] **Step 1: Create root `pyproject.toml`**

```toml
# pyproject.toml
[tool.uv.workspace]
members = ["services/das"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["services/das/tests"]
```

- [ ] **Step 2: Create `docker-compose.yml`**

```yaml
# docker-compose.yml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: dstn
      POSTGRES_USER: dstn
      POSTGRES_PASSWORD: dstn
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  pgdata:
```

- [ ] **Step 3: Create `.env.example`**

```bash
# .env.example
DATABASE_URL=postgresql+asyncpg://dstn:dstn@localhost:5432/dstn
CANADABUYS_BASE_URL=https://canadabuys.canada.ca/openapi/v1
OPEN_GOV_DATASET_URL=https://open.canada.ca/data/en/datastore/dump/d8f85d91-7dec-4fd1-8055-483b77225d8b
ISSUER_AGENT_ADMIN_URL=http://localhost:8021
ISSUER_AGENT_API_KEY=change-me
SYNC_INTERVAL_MINUTES=60
```

- [ ] **Step 4: Create `services/das/pyproject.toml`**

```toml
[project]
name = "das"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "httpx>=0.27.0",
    "apscheduler>=3.10.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "alembic>=1.13.0",
    "asyncpg>=0.29.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
test = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "respx>=0.21.0",
    "aiosqlite>=0.20.0",
]
```

- [ ] **Step 5: Start postgres and verify connectivity**

```bash
docker compose up -d postgres
docker compose exec postgres psql -U dstn -c "SELECT version();"
```

Expected: PostgreSQL 16.x version string.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml docker-compose.yml .env.example services/das/pyproject.toml
git commit -m "feat: scaffold project repo and dev environment"
```

---

### Task 2: Shared Config, Database Engine, and ORM Models

**Files:**
- Create: `shared/__init__.py`
- Create: `shared/config.py`
- Create: `shared/db.py`
- Create: `shared/models.py`
- Create: `alembic/alembic.ini`
- Create: `alembic/env.py`

- [ ] **Step 1: Write the failing test**

```python
# services/das/tests/test_models.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from shared.models import Base, SupplierRecord, SupplierStatus
from datetime import date, datetime, timezone

@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        yield s

async def test_supplier_record_create(session):
    record = SupplierRecord(
        business_number="123456789",
        business_name="Acme Corp",
        status=SupplierStatus.PENDING_REGISTRATION,
        data_sources=["open_gov"],
        last_synced_at=datetime.now(timezone.utc),
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    assert record.status == SupplierStatus.PENDING_REGISTRATION
    assert record.credential_issued is False
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd services/das && python -m pytest tests/test_models.py -v
```

Expected: `ImportError: No module named 'shared'`

- [ ] **Step 3: Create `shared/config.py`**

```python
# shared/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+asyncpg://dstn:dstn@localhost:5432/dstn"
    canadabuys_base_url: str = "https://canadabuys.canada.ca/openapi/v1"
    open_gov_dataset_url: str = "https://open.canada.ca/data/en/datastore/dump/d8f85d91-7dec-4fd1-8055-483b77225d8b"
    issuer_agent_admin_url: str = "http://localhost:8021"
    issuer_agent_api_key: str = "change-me"
    sync_interval_minutes: int = 60

settings = Settings()
```

- [ ] **Step 4: Create `shared/models.py`**

```python
# shared/models.py
import enum
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Enum, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

class Base(DeclarativeBase):
    pass

class SupplierStatus(str, enum.Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    PENDING_REGISTRATION = "pending_registration"

class SupplierRecord(Base):
    __tablename__ = "supplier_records"

    business_number: Mapped[str] = mapped_column(String(15), primary_key=True)
    business_name: Mapped[str] = mapped_column(String(255))
    status: Mapped[SupplierStatus] = mapped_column(Enum(SupplierStatus))
    data_sources: Mapped[str] = mapped_column(Text, default="[]")  # JSON list
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    credential_issued: Mapped[bool] = mapped_column(Boolean, default=False)
    credential_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    did_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
```

- [ ] **Step 5: Create `shared/db.py`**

```python
# shared/db.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from shared.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```

- [ ] **Step 6: Add `shared` to sys.path in test conftest**

```python
# services/das/tests/conftest.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # repo root
```

- [ ] **Step 7: Run test to verify it passes**

```bash
cd services/das && python -m pytest tests/test_models.py -v
```

Expected: `PASSED` — `test_supplier_record_create`

- [ ] **Step 8: Set up Alembic**

```bash
cd alembic && alembic init .
```

Edit `alembic/env.py` — replace the target_metadata line:
```python
# alembic/env.py  (add at top after imports)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared.models import Base
from shared.config import settings

# replace the existing target_metadata = None line:
target_metadata = Base.metadata

# replace the existing run_migrations_online get_url() call:
def run_migrations_online() -> None:
    url = settings.database_url.replace("+asyncpg", "")  # Alembic uses sync driver
    connectable = engine_from_config({"sqlalchemy.url": url}, prefix="sqlalchemy.")
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
```

```bash
alembic revision --autogenerate -m "create supplier_records table"
alembic upgrade head
```

Expected: migration applied, `supplier_records` table exists in PostgreSQL.

- [ ] **Step 9: Commit**

```bash
git add shared/ alembic/
git commit -m "feat: add shared config, DB engine, SupplierRecord ORM model, Alembic migration"
```

---

### Task 3: CanadaBuys Connector

**Files:**
- Create: `services/das/das/connectors/base.py`
- Create: `services/das/das/connectors/canadabuys.py`
- Test: `services/das/tests/test_canadabuys.py`

- [ ] **Step 1: Write the failing test**

```python
# services/das/tests/test_canadabuys.py
import pytest
import respx
import httpx
from das.connectors.canadabuys import CanadaBuysConnector, ContractRecord

SAMPLE_RESPONSE = {
    "contracts": [
        {
            "vendor_name": "Acme Corp",
            "business_number": "123456789",
            "contract_date": "2024-03-15",
            "contract_period_end": "2025-03-14",
            "total_value": 150000.0,
            "status": "active",
            "reference_number": "CB-2024-001",
        }
    ]
}

@pytest.mark.asyncio
@respx.mock
async def test_fetch_contracts_returns_records():
    respx.get("https://canadabuys.canada.ca/openapi/v1/contracts").mock(
        return_value=httpx.Response(200, json=SAMPLE_RESPONSE)
    )
    connector = CanadaBuysConnector(base_url="https://canadabuys.canada.ca/openapi/v1")
    records = await connector.fetch_contracts()
    assert len(records) == 1
    assert records[0].business_number == "123456789"
    assert records[0].vendor_name == "Acme Corp"
    assert records[0].status == "active"

@pytest.mark.asyncio
@respx.mock
async def test_fetch_contracts_handles_http_error():
    respx.get("https://canadabuys.canada.ca/openapi/v1/contracts").mock(
        return_value=httpx.Response(503)
    )
    connector = CanadaBuysConnector(base_url="https://canadabuys.canada.ca/openapi/v1")
    records = await connector.fetch_contracts()
    assert records == []  # graceful degradation on error
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd services/das && python -m pytest tests/test_canadabuys.py -v
```

Expected: `ImportError: cannot import name 'CanadaBuysConnector'`

- [ ] **Step 3: Create `das/connectors/base.py`**

```python
# services/das/das/connectors/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date

@dataclass
class ContractRecord:
    business_number: str        # CRA business number (may be empty for name-only records)
    vendor_name: str
    contract_date: date
    contract_end_date: date | None
    total_value: float
    status: str                 # "active" | "cancelled" | "closed"
    reference_number: str
    source: str = ""            # which connector produced this record

class BaseConnector(ABC):
    @abstractmethod
    async def fetch_contracts(self) -> list[ContractRecord]:
        """Return all contract records from this data source. Return [] on error."""
```

- [ ] **Step 4: Create `das/connectors/canadabuys.py`**

```python
# services/das/das/connectors/canadabuys.py
import logging
from datetime import date
import httpx
from das.connectors.base import BaseConnector, ContractRecord

logger = logging.getLogger(__name__)

class CanadaBuysConnector(BaseConnector):
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def fetch_contracts(self) -> list[ContractRecord]:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.get(f"{self.base_url}/contracts")
                r.raise_for_status()
                data = r.json()
        except Exception as exc:
            logger.warning("CanadaBuys fetch failed: %s", exc)
            return []

        records = []
        for item in data.get("contracts", []):
            try:
                records.append(ContractRecord(
                    business_number=item.get("business_number", ""),
                    vendor_name=item["vendor_name"],
                    contract_date=date.fromisoformat(item["contract_date"]),
                    contract_end_date=date.fromisoformat(item["contract_period_end"]) if item.get("contract_period_end") else None,
                    total_value=float(item.get("total_value", 0)),
                    status=item.get("status", "active"),
                    reference_number=item["reference_number"],
                    source="canadabuys",
                ))
            except (KeyError, ValueError) as exc:
                logger.warning("Skipping malformed CanadaBuys record: %s", exc)
        return records
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd services/das && python -m pytest tests/test_canadabuys.py -v
```

Expected: both tests `PASSED`

- [ ] **Step 6: Commit**

```bash
git add services/das/das/connectors/
git commit -m "feat: add CanadaBuys connector with graceful HTTP error handling"
```

---

### Task 4: Open Government Connector

**Files:**
- Create: `services/das/das/connectors/open_gov.py`
- Create: `services/das/das/connectors/future_auth.py`
- Test: `services/das/tests/test_open_gov.py`

The Open Government procurement dataset is a CSV. The relevant columns are: `vendor_name`, `reference_number`, `contract_date`, `contract_period_end`, `contract_value`, and optionally `vendor_business_number`.

- [ ] **Step 1: Write the failing test**

```python
# services/das/tests/test_open_gov.py
import pytest
import respx
import httpx
from das.connectors.open_gov import OpenGovConnector

SAMPLE_CSV = (
    "reference_number,vendor_name,vendor_business_number,contract_date,"
    "contract_period_end,contract_value,status\r\n"
    "OG-2024-001,Widgets Ltd,987654321,2024-01-10,2025-01-09,50000.0,active\r\n"
    "OG-2024-002,No BN Corp,,2024-02-20,,25000.0,active\r\n"
)

DATASET_URL = "https://open.canada.ca/data/en/datastore/dump/d8f85d91-7dec-4fd1-8055-483b77225d8b"

@pytest.mark.asyncio
@respx.mock
async def test_fetch_contracts_parses_csv():
    respx.get(DATASET_URL).mock(return_value=httpx.Response(200, text=SAMPLE_CSV))
    connector = OpenGovConnector(dataset_url=DATASET_URL)
    records = await connector.fetch_contracts()
    assert len(records) == 2
    assert records[0].business_number == "987654321"
    assert records[0].vendor_name == "Widgets Ltd"
    assert records[1].business_number == ""   # no BN in source data

@pytest.mark.asyncio
@respx.mock
async def test_fetch_contracts_handles_error():
    respx.get(DATASET_URL).mock(return_value=httpx.Response(404))
    connector = OpenGovConnector(dataset_url=DATASET_URL)
    records = await connector.fetch_contracts()
    assert records == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd services/das && python -m pytest tests/test_open_gov.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Create `das/connectors/open_gov.py`**

```python
# services/das/das/connectors/open_gov.py
import csv
import io
import logging
from datetime import date
import httpx
from das.connectors.base import BaseConnector, ContractRecord

logger = logging.getLogger(__name__)

class OpenGovConnector(BaseConnector):
    def __init__(self, dataset_url: str):
        self.dataset_url = dataset_url

    async def fetch_contracts(self) -> list[ContractRecord]:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.get(self.dataset_url)
                r.raise_for_status()
                text = r.text
        except Exception as exc:
            logger.warning("Open Gov fetch failed: %s", exc)
            return []

        records = []
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            try:
                end_date_raw = row.get("contract_period_end", "").strip()
                records.append(ContractRecord(
                    business_number=row.get("vendor_business_number", "").strip(),
                    vendor_name=row["vendor_name"].strip(),
                    contract_date=date.fromisoformat(row["contract_date"].strip()),
                    contract_end_date=date.fromisoformat(end_date_raw) if end_date_raw else None,
                    total_value=float(row.get("contract_value", 0) or 0),
                    status=row.get("status", "active").strip(),
                    reference_number=row["reference_number"].strip(),
                    source="open_gov",
                ))
            except (KeyError, ValueError) as exc:
                logger.warning("Skipping malformed Open Gov row: %s", exc)
        return records
```

- [ ] **Step 4: Create `das/connectors/future_auth.py`** (pluggable stub)

```python
# services/das/das/connectors/future_auth.py
import logging
from das.connectors.base import BaseConnector, ContractRecord

logger = logging.getLogger(__name__)

class FutureAuthConnector(BaseConnector):
    """Pluggable adapter for the future authoritative GoC data source (per AMD002).
    Replace this implementation when the source is determined."""

    async def fetch_contracts(self) -> list[ContractRecord]:
        logger.info("FutureAuthConnector: no source configured — returning empty")
        return []
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd services/das && python -m pytest tests/test_open_gov.py -v
```

Expected: both tests `PASSED`

- [ ] **Step 6: Commit**

```bash
git add services/das/das/connectors/open_gov.py services/das/das/connectors/future_auth.py
git commit -m "feat: add Open Government connector (CSV) and FutureAuth stub"
```

---

### Task 5: Status Derivation Engine

**Files:**
- Create: `services/das/das/engine/status_derivation.py`
- Test: `services/das/tests/test_status_derivation.py`

The engine takes all contract records from all connectors, groups by business_number (or vendor_name when BN is absent), and derives status.

- [ ] **Step 1: Write the failing test**

```python
# services/das/tests/test_status_derivation.py
import pytest
from datetime import date, timedelta
from das.connectors.base import ContractRecord
from das.engine.status_derivation import StatusDerivationEngine, DerivedStatus

def make_record(bn="123456789", name="Acme Corp", status="active", end_days_ahead=30):
    return ContractRecord(
        business_number=bn,
        vendor_name=name,
        contract_date=date.today() - timedelta(days=90),
        contract_end_date=date.today() + timedelta(days=end_days_ahead),
        total_value=100000.0,
        status=status,
        reference_number="REF-001",
        source="canadabuys",
    )

def test_active_supplier_derives_active():
    engine = StatusDerivationEngine()
    result = engine.derive([make_record()])
    assert len(result) == 1
    assert result["123456789"].status == "active"
    assert result["123456789"].business_name == "Acme Corp"

def test_cancelled_contract_derives_revoked():
    engine = StatusDerivationEngine()
    result = engine.derive([make_record(status="cancelled")])
    assert result["123456789"].status == "revoked"

def test_multi_source_active_wins_over_single_cancelled():
    engine = StatusDerivationEngine()
    records = [
        make_record(bn="111", name="Corp A", status="active"),
        make_record(bn="111", name="Corp A", status="cancelled"),
    ]
    result = engine.derive(records)
    # At least one active contract → supplier is active
    assert result["111"].status == "active"

def test_no_bn_falls_back_to_vendor_name_key():
    engine = StatusDerivationEngine()
    records = [make_record(bn="", name="No BN Corp")]
    result = engine.derive(records)
    # keyed by vendor name when BN absent
    assert "no_bn_corp" in result or any(v.business_name == "No BN Corp" for v in result.values())
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd services/das && python -m pytest tests/test_status_derivation.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Create `das/engine/status_derivation.py`**

```python
# services/das/das/engine/status_derivation.py
import re
from dataclasses import dataclass
from das.connectors.base import ContractRecord

@dataclass
class DerivedStatus:
    business_number: str
    business_name: str
    status: str                 # "active" | "revoked"
    data_sources: list[str]

def _normalize_name(name: str) -> str:
    return re.sub(r"\s+", "_", name.strip().lower())

class StatusDerivationEngine:
    def derive(self, records: list[ContractRecord]) -> dict[str, DerivedStatus]:
        """Return a dict keyed by business_number (or normalized vendor name) → DerivedStatus."""
        groups: dict[str, list[ContractRecord]] = {}
        for r in records:
            key = r.business_number.strip() if r.business_number.strip() else _normalize_name(r.vendor_name)
            groups.setdefault(key, []).append(r)

        result: dict[str, DerivedStatus] = {}
        for key, group in groups.items():
            sources = list({r.source for r in group})
            business_name = group[0].vendor_name
            business_number = next((r.business_number for r in group if r.business_number), key)

            # Active if at least one non-cancelled, non-revoked contract record
            any_active = any(r.status not in ("cancelled", "revoked", "terminated") for r in group)
            status = "active" if any_active else "revoked"

            result[key] = DerivedStatus(
                business_number=business_number,
                business_name=business_name,
                status=status,
                data_sources=sources,
            )
        return result
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd services/das && python -m pytest tests/test_status_derivation.py -v
```

Expected: all 4 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add services/das/das/engine/status_derivation.py services/das/tests/test_status_derivation.py
git commit -m "feat: add Status Derivation Engine with multi-source aggregation"
```

---

### Task 6: Pending State Store

**Files:**
- Create: `services/das/das/engine/pending_state.py`
- Test: `services/das/tests/test_pending_state.py`

The Pending State Store upserts DerivedStatus into the `supplier_records` table. Suppliers without a registered passkey (did_key is NULL) stay in `pending_registration` status.

- [ ] **Step 1: Write the failing test**

```python
# services/das/tests/test_pending_state.py
import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from shared.models import Base, SupplierRecord, SupplierStatus
from das.engine.pending_state import PendingStateStore
from das.engine.status_derivation import DerivedStatus

@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s

async def test_upsert_new_supplier_sets_pending(db_session):
    store = PendingStateStore(db_session)
    derived = DerivedStatus("123456789", "Acme Corp", "active", ["canadabuys"])
    await store.upsert(derived)
    record = await db_session.get(SupplierRecord, "123456789")
    assert record is not None
    assert record.status == SupplierStatus.PENDING_REGISTRATION
    assert record.credential_issued is False

async def test_upsert_registered_supplier_stays_active(db_session):
    # Pre-populate a supplier that already has a did_key (passkey registered)
    record = SupplierRecord(
        business_number="999888777",
        business_name="Registered Corp",
        status=SupplierStatus.ACTIVE,
        data_sources='["canadabuys"]',
        last_synced_at=datetime.now(timezone.utc),
        credential_issued=True,
        did_key="did:key:ztest",
    )
    db_session.add(record)
    await db_session.commit()

    store = PendingStateStore(db_session)
    derived = DerivedStatus("999888777", "Registered Corp", "active", ["open_gov"])
    await store.upsert(derived)

    await db_session.refresh(record)
    assert record.status == SupplierStatus.ACTIVE  # not downgraded to pending
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd services/das && python -m pytest tests/test_pending_state.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Create `das/engine/pending_state.py`**

```python
# services/das/das/engine/pending_state.py
import json
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from shared.models import SupplierRecord, SupplierStatus
from das.engine.status_derivation import DerivedStatus

class PendingStateStore:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(self, derived: DerivedStatus) -> SupplierRecord:
        existing = await self.session.get(SupplierRecord, derived.business_number)
        now = datetime.now(timezone.utc)

        if existing is None:
            existing = SupplierRecord(
                business_number=derived.business_number,
                business_name=derived.business_name,
                status=SupplierStatus.PENDING_REGISTRATION,
                data_sources=json.dumps(derived.data_sources),
                last_synced_at=now,
                credential_issued=False,
            )
            self.session.add(existing)
        else:
            existing.business_name = derived.business_name
            existing.data_sources = json.dumps(derived.data_sources)
            existing.last_synced_at = now

            if derived.status == "revoked":
                existing.status = SupplierStatus.REVOKED
            elif existing.did_key and existing.status == SupplierStatus.PENDING_REGISTRATION:
                # Passkey was registered while status was pending — promote to active
                existing.status = SupplierStatus.ACTIVE
            # If already ACTIVE or REVOKED with a passkey, leave status unchanged here;
            # the Credential Trigger handles status-change events.

        await self.session.commit()
        return existing
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd services/das && python -m pytest tests/test_pending_state.py -v
```

Expected: both tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add services/das/das/engine/pending_state.py services/das/tests/test_pending_state.py
git commit -m "feat: add PendingStateStore — upserts supplier status, preserves registered state"
```

---

### Task 7: Credential Trigger Stub

**Files:**
- Create: `services/das/das/triggers/credential_trigger.py`
- Test: `services/das/tests/test_credential_trigger.py`

The Credential Trigger calls the Aries Issuer Agent admin API to issue or revoke credentials. In Part 1 this is a stub — the interface is defined and tested with mocks. Part 2 wires it to the real ACA-Py agent.

- [ ] **Step 1: Write the failing test**

```python
# services/das/tests/test_credential_trigger.py
import pytest
import respx
import httpx
from das.triggers.credential_trigger import CredentialTrigger, TriggerEvent

ADMIN_URL = "http://issuer:8021"

@pytest.mark.asyncio
@respx.mock
async def test_trigger_issue_calls_issuer_agent():
    respx.post(f"{ADMIN_URL}/issue-credential-2.0/send").mock(
        return_value=httpx.Response(200, json={"cred_ex_id": "abc-123"})
    )
    trigger = CredentialTrigger(admin_url=ADMIN_URL, api_key="test-key")
    result = await trigger.issue("123456789", "Acme Corp", "did:key:zTestDID")
    assert result == "abc-123"

@pytest.mark.asyncio
@respx.mock
async def test_trigger_revoke_calls_issuer_agent():
    respx.post(f"{ADMIN_URL}/revocation/revoke").mock(
        return_value=httpx.Response(200, json={"result": "ok"})
    )
    trigger = CredentialTrigger(admin_url=ADMIN_URL, api_key="test-key")
    result = await trigger.revoke("cred-123", "rev-reg-001")
    assert result is True

@pytest.mark.asyncio
@respx.mock
async def test_trigger_issue_handles_agent_error():
    respx.post(f"{ADMIN_URL}/issue-credential-2.0/send").mock(
        return_value=httpx.Response(500)
    )
    trigger = CredentialTrigger(admin_url=ADMIN_URL, api_key="test-key")
    result = await trigger.issue("123456789", "Acme Corp", "did:key:zTestDID")
    assert result is None  # graceful failure
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd services/das && python -m pytest tests/test_credential_trigger.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Create `das/triggers/credential_trigger.py`**

```python
# services/das/das/triggers/credential_trigger.py
import logging
import httpx

logger = logging.getLogger(__name__)

class TriggerEvent:
    ISSUE = "issue"
    REVOKE = "revoke"

class CredentialTrigger:
    """Calls the Aries Issuer Agent admin API to issue or revoke credentials.
    Populated with full request body in Part 2 once schema/cred_def IDs are known."""

    def __init__(self, admin_url: str, api_key: str):
        self.admin_url = admin_url.rstrip("/")
        self.headers = {"x-api-key": api_key}

    async def issue(self, business_number: str, business_name: str, holder_did: str) -> str | None:
        """Request credential issuance. Returns cred_ex_id or None on failure."""
        payload = {
            "auto_remove": False,
            "comment": f"DSTN credential for {business_number}",
            "connection_id": "",          # filled in Part 2 with TEE Holder connection ID
            "cred_def_id": "",            # filled in Part 2 once anchored on Stratos
            "credential_preview": {
                "@type": "issue-credential/2.0/credential-preview",
                "attributes": [
                    {"name": "business_number", "value": business_number},
                    {"name": "business_name", "value": business_name},
                    {"name": "holder_did", "value": holder_did},
                    {"name": "supplier_status", "value": "active"},
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
            logger.error("Credential issuance trigger failed for %s: %s", business_number, exc)
            return None

    async def revoke(self, cred_ex_id: str, rev_reg_id: str) -> bool:
        """Request credential revocation. Returns True on success."""
        payload = {"cred_ex_id": cred_ex_id, "rev_reg_id": rev_reg_id, "publish": True}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(
                    f"{self.admin_url}/revocation/revoke",
                    json=payload,
                    headers=self.headers,
                )
                r.raise_for_status()
                return True
        except Exception as exc:
            logger.error("Credential revocation trigger failed for %s: %s", cred_ex_id, exc)
            return False
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd services/das && python -m pytest tests/test_credential_trigger.py -v
```

Expected: all 3 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add services/das/das/triggers/ services/das/tests/test_credential_trigger.py
git commit -m "feat: add CredentialTrigger stub — interface defined, wired to ACA-Py in Part 2"
```

---

### Task 8: Sync Scheduler and Service Entrypoint

**Files:**
- Create: `services/das/das/scheduler.py`
- Create: `services/das/das/main.py`
- Test: `services/das/tests/test_scheduler.py`

- [ ] **Step 1: Write the failing test**

```python
# services/das/tests/test_scheduler.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from das.scheduler import run_sync_cycle

async def test_sync_cycle_calls_all_connectors():
    mock_cb_records = [MagicMock(business_number="111", vendor_name="Corp A", status="active")]
    mock_og_records = []

    with patch("das.scheduler.CanadaBuysConnector") as MockCB, \
         patch("das.scheduler.OpenGovConnector") as MockOG, \
         patch("das.scheduler.FutureAuthConnector") as MockFA, \
         patch("das.scheduler.StatusDerivationEngine") as MockEngine, \
         patch("das.scheduler.async_session_factory") as MockSession:

        MockCB.return_value.fetch_contracts = AsyncMock(return_value=mock_cb_records)
        MockOG.return_value.fetch_contracts = AsyncMock(return_value=mock_og_records)
        MockFA.return_value.fetch_contracts = AsyncMock(return_value=[])
        MockEngine.return_value.derive = MagicMock(return_value={})
        MockSession.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

        await run_sync_cycle()

        MockCB.return_value.fetch_contracts.assert_called_once()
        MockOG.return_value.fetch_contracts.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd services/das && python -m pytest tests/test_scheduler.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Create `das/scheduler.py`**

```python
# services/das/das/scheduler.py
import asyncio
import logging
from shared.config import settings
from shared.db import async_session_factory
from das.connectors.canadabuys import CanadaBuysConnector
from das.connectors.open_gov import OpenGovConnector
from das.connectors.future_auth import FutureAuthConnector
from das.engine.status_derivation import StatusDerivationEngine
from das.engine.pending_state import PendingStateStore
from das.triggers.credential_trigger import CredentialTrigger

logger = logging.getLogger(__name__)

async def run_sync_cycle() -> None:
    logger.info("Starting data sync cycle")
    cb = CanadaBuysConnector(base_url=settings.canadabuys_base_url)
    og = OpenGovConnector(dataset_url=settings.open_gov_dataset_url)
    fa = FutureAuthConnector()

    all_records = []
    for connector in (cb, og, fa):
        records = await connector.fetch_contracts()
        all_records.extend(records)

    logger.info("Fetched %d total contract records", len(all_records))

    engine = StatusDerivationEngine()
    derived = engine.derive(all_records)
    logger.info("Derived status for %d suppliers", len(derived))

    trigger = CredentialTrigger(
        admin_url=settings.issuer_agent_admin_url,
        api_key=settings.issuer_agent_api_key,
    )

    async with async_session_factory() as session:
        store = PendingStateStore(session)
        for derived_status in derived.values():
            record = await store.upsert(derived_status)
            # Trigger issuance for active suppliers with a registered passkey
            if derived_status.status == "active" and record.did_key and not record.credential_issued:
                cred_ex_id = await trigger.issue(
                    record.business_number,
                    record.business_name,
                    record.did_key,
                )
                if cred_ex_id:
                    record.credential_issued = True
                    record.credential_id = cred_ex_id
                    await session.commit()
            elif derived_status.status == "revoked" and record.credential_issued and record.credential_id:
                await trigger.revoke(record.credential_id, rev_reg_id="")  # rev_reg_id filled in Part 2
    logger.info("Sync cycle complete")
```

- [ ] **Step 4: Create `das/main.py`**

```python
# services/das/das/main.py
import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from shared.config import settings
from das.scheduler import run_sync_cycle

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_sync_cycle, "interval", minutes=settings.sync_interval_minutes, id="sync")
    scheduler.start()
    logging.getLogger(__name__).info(
        "DAS started — sync every %d minutes", settings.sync_interval_minutes
    )
    # Run once immediately on startup
    await run_sync_cycle()
    # Keep running
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd services/das && python -m pytest tests/test_scheduler.py -v
```

Expected: `PASSED`

- [ ] **Step 6: Run the full test suite**

```bash
cd services/das && python -m pytest tests/ -v
```

Expected: all tests pass (no failures).

- [ ] **Step 7: Commit**

```bash
git add services/das/das/scheduler.py services/das/das/main.py services/das/tests/test_scheduler.py
git commit -m "feat: add sync scheduler and DAS entrypoint — runs all connectors on interval"
```

---

## Part 1 Complete

Run the full test suite one final time to confirm:

```bash
cd services/das && python -m pytest tests/ -v --tb=short
```

Expected: all tests green.

**What's working after Part 1:**
- PostgreSQL schema and Alembic migrations
- CanadaBuys and Open Gov contract data ingestion
- Status derivation from aggregated records
- Pending State Store persisting supplier status to DB
- Credential Trigger stub with correct interface
- APScheduler running sync cycles on configured interval

**Part 2 will:** wire the ACA-Py Issuer Agent, anchor the AnonCreds schema and credential definition on Stratos Blockchain, implement the `did:stratos` resolver, and replace the CredentialTrigger stub with full ACA-Py calls.
