# services/verification/tests/test_verify.py
import pytest
import respx
import httpx
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from shared.models import Base, EncryptedCredential, PasskeyRecord
from verification.verify import VerificationService

STRATOS_URL = "https://stratos-api.example.org/api/v1"
REV_REG_ID = "did:stratos:issuer/rev_reg/1"

@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s

@pytest.mark.asyncio
@respx.mock
async def test_verify_active_supplier(session):
    session.add(PasskeyRecord(
        credential_id=b"cred-id-1", business_number="123456789",
        public_key_cose=b"\x00" * 10, did_key="did:key:zTest", sign_count=0,
        created_at=datetime.now(timezone.utc),
    ))
    session.add(EncryptedCredential(
        did_key="did:key:zTest", ciphertext=b"enc", nonce=b"nonce000000",
        cred_ex_id="cred-001", updated_at=datetime.now(timezone.utc),
    ))
    await session.commit()

    respx.get(f"{STRATOS_URL}/anoncreds/revocation-registry/{REV_REG_ID}/status").mock(
        return_value=httpx.Response(200, json={"revoked": False})
    )
    svc = VerificationService(session, stratos_url=STRATOS_URL, stratos_key="key", rev_reg_id=REV_REG_ID)
    result = await svc.verify("123456789")
    assert result["status"] == "active"
    assert result["revoked"] is False
    assert result["business_number"] == "123456789"

@pytest.mark.asyncio
async def test_verify_unknown_supplier(session):
    svc = VerificationService(session, stratos_url=STRATOS_URL, stratos_key="key", rev_reg_id=REV_REG_ID)
    result = await svc.verify("000000000")
    assert result["status"] == "not_found"
