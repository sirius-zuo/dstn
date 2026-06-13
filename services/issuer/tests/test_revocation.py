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
