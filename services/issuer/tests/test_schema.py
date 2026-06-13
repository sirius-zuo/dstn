import pytest
import respx
import httpx
from issuer.schema import SchemaManager, DSTN_SCHEMA_ATTRS, DSTN_SCHEMA_NAME, DSTN_SCHEMA_VERSION

STRATOS_URL = "https://stratos-api.example.org/api/v1"
ISSUER_DID = "did:stratos:issuer001"

@pytest.mark.asyncio
@respx.mock
async def test_ensure_schema_anchors_if_not_exists():
    schema_id = f"{ISSUER_DID}/anoncreds/v0/SCHEMA/{DSTN_SCHEMA_NAME}/{DSTN_SCHEMA_VERSION}"
    cred_def_id = f"{ISSUER_DID}/anoncreds/v0/CLAIM_DEF/1/default"
    rev_reg_id = f"{ISSUER_DID}/anoncreds/v0/REV_REG_DEF/1/default/0"

    respx.post(f"{STRATOS_URL}/anoncreds/schema").mock(
        return_value=httpx.Response(200, json={"schema_id": schema_id})
    )
    respx.post(f"{STRATOS_URL}/anoncreds/credential-definition").mock(
        return_value=httpx.Response(200, json={"cred_def_id": cred_def_id})
    )
    respx.post(f"{STRATOS_URL}/anoncreds/revocation-registry").mock(
        return_value=httpx.Response(200, json={"rev_reg_id": rev_reg_id})
    )

    manager = SchemaManager(api_url=STRATOS_URL, api_key="key", issuer_did=ISSUER_DID)
    result = await manager.ensure_schema_and_cred_def()
    assert result["schema_id"] == schema_id
    assert result["cred_def_id"] == cred_def_id
    assert result["rev_reg_id"] == rev_reg_id

def test_dstn_schema_has_required_attributes():
    assert "business_number" in DSTN_SCHEMA_ATTRS
    assert "business_name" in DSTN_SCHEMA_ATTRS
    assert "supplier_status" in DSTN_SCHEMA_ATTRS
    assert "issue_date" in DSTN_SCHEMA_ATTRS
    assert "expiry_date" in DSTN_SCHEMA_ATTRS
