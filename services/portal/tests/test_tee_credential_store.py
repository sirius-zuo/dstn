# services/portal/tests/test_tee_credential_store.py
import pytest
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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

@pytest.mark.asyncio
async def test_tee_store_and_retrieve(session):
    store = TEECredentialStore(session)
    await store.store(DID_KEY, SAMPLE_CRED)
    result = await store.retrieve(DID_KEY)
    assert json.loads(result)["business_number"] == "999"

@pytest.mark.asyncio
async def test_tee_store_ciphertext_differs_from_plaintext(session):
    store = TEECredentialStore(session)
    await store.store(DID_KEY, SAMPLE_CRED)
    rec = await session.get(EncryptedCredential, DID_KEY)
    assert rec.ciphertext != SAMPLE_CRED.encode()
