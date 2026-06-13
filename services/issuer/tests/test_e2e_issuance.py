# services/issuer/tests/test_e2e_issuance.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "services" / "das"))

import pytest
import respx
import httpx
from das.connectors.canadabuys import CanadaBuysConnector
from das.engine.status_derivation import StatusDerivationEngine
from das.triggers.credential_trigger import CredentialTrigger

CANADABUYS_URL = "https://canadabuys.canada.ca/openapi/v1"
ISSUER_URL = "http://issuer:8021"

SAMPLE_CONTRACTS = {"contracts": [{
    "vendor_name": "Acme Corp",
    "business_number": "123456789",
    "contract_date": "2024-01-15",
    "contract_period_end": "2025-01-14",
    "total_value": 200000.0,
    "status": "active",
    "reference_number": "CB-E2E-001",
}]}

@pytest.mark.asyncio
@respx.mock
async def test_full_issuance_flow():
    respx.get(f"{CANADABUYS_URL}/contracts").mock(
        return_value=httpx.Response(200, json=SAMPLE_CONTRACTS)
    )
    respx.get(f"{ISSUER_URL}/connections").mock(
        return_value=httpx.Response(200, json={"results": [{"connection_id": "conn-abc"}]})
    )
    issue_call = respx.post(f"{ISSUER_URL}/issue-credential-2.0/send").mock(
        return_value=httpx.Response(200, json={"cred_ex_id": "cred-e2e-001"})
    )

    connector = CanadaBuysConnector(base_url=CANADABUYS_URL)
    records = await connector.fetch_contracts()
    engine = StatusDerivationEngine()
    derived = engine.derive(records)

    trigger = CredentialTrigger(admin_url=ISSUER_URL, api_key="test")
    cred_ex_id = None
    for status in derived.values():
        if status.status == "active":
            cred_ex_id = await trigger.issue(
                business_number=status.business_number,
                business_name=status.business_name,
                holder_did="did:key:zTestHolder",
            )

    assert issue_call.called
    assert cred_ex_id == "cred-e2e-001"
    import json
    body = json.loads(issue_call.calls[0].request.content)
    attrs = {a["name"]: a["value"] for a in body["credential_preview"]["attributes"]}
    assert attrs["business_number"] == "123456789"
    assert attrs["supplier_status"] == "active"
