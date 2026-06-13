# services/issuer/tests/test_stratos_client.py
import pytest
import respx
import httpx
from issuer.stratos_client import StratosClient, DIDDocument

STRATOS_URL = "https://stratos-api.example.org/api/v1"

@pytest.mark.asyncio
@respx.mock
async def test_resolve_did_returns_document():
    test_did = "did:stratos:abc123"
    respx.get(f"{STRATOS_URL}/did/abc123").mock(
        return_value=httpx.Response(200, json={
            "id": test_did,
            "verificationMethod": [{"id": f"{test_did}#key-1", "publicKeyMultibase": "zAbc"}],
        })
    )
    client = StratosClient(api_url=STRATOS_URL, api_key="key")
    doc = await client.resolve_did("did:stratos:abc123")
    assert doc.id == test_did

@pytest.mark.asyncio
@respx.mock
async def test_anchor_schema_returns_schema_id():
    respx.post(f"{STRATOS_URL}/anoncreds/schema").mock(
        return_value=httpx.Response(200, json={"schema_id": "did:stratos:abc123/anoncreds/v0/SCHEMA/GoCSupplier/1.0"})
    )
    client = StratosClient(api_url=STRATOS_URL, api_key="key")
    schema_id = await client.anchor_schema(issuer_did="did:stratos:abc123", name="GoCSupplier", version="1.0", attr_names=["business_number"])
    assert "GoCSupplier" in schema_id
