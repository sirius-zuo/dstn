import pytest
import respx
import httpx
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
    doc = await resolver._fetch_did_document(test_did)
    assert doc["id"] == test_did
    assert len(doc["verificationMethod"]) == 1
