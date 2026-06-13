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
    assert rec.ciphertext != cred_json.encode()
