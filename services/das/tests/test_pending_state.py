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
