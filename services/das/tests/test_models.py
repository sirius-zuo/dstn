import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from shared.models import Base, SupplierRecord, SupplierStatus
from datetime import datetime, timezone

@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()

async def test_supplier_record_create(session):
    record = SupplierRecord(
        business_number="123456789",
        business_name="Acme Corp",
        status=SupplierStatus.PENDING_REGISTRATION,
        data_sources='["open_gov"]',
        last_synced_at=datetime.now(timezone.utc),
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    assert record.status == SupplierStatus.PENDING_REGISTRATION
    assert record.credential_issued is False
