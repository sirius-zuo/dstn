import pytest
import respx
import httpx
from das.triggers.credential_trigger import CredentialTrigger, TriggerEvent

ADMIN_URL = "http://issuer:8021"

@pytest.mark.asyncio
@respx.mock
async def test_trigger_issue_calls_issuer_agent():
    respx.get(f"{ADMIN_URL}/connections").mock(
        return_value=httpx.Response(200, json={"results": [{"connection_id": "conn-test"}]})
    )
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
    respx.get(f"{ADMIN_URL}/connections").mock(
        return_value=httpx.Response(200, json={"results": [{"connection_id": "conn-test"}]})
    )
    respx.post(f"{ADMIN_URL}/issue-credential-2.0/send").mock(
        return_value=httpx.Response(500)
    )
    trigger = CredentialTrigger(admin_url=ADMIN_URL, api_key="test-key")
    result = await trigger.issue("123456789", "Acme Corp", "did:key:zTestDID")
    assert result is None  # graceful failure
