import pytest
import respx
import httpx
from das.connectors.canadabuys import CanadaBuysConnector, ContractRecord

SAMPLE_RESPONSE = {
    "contracts": [
        {
            "vendor_name": "Acme Corp",
            "business_number": "123456789",
            "contract_date": "2024-03-15",
            "contract_period_end": "2025-03-14",
            "total_value": 150000.0,
            "status": "active",
            "reference_number": "CB-2024-001",
        }
    ]
}

@pytest.mark.asyncio
@respx.mock
async def test_fetch_contracts_returns_records():
    respx.get("https://canadabuys.canada.ca/openapi/v1/contracts").mock(
        return_value=httpx.Response(200, json=SAMPLE_RESPONSE)
    )
    connector = CanadaBuysConnector(base_url="https://canadabuys.canada.ca/openapi/v1")
    records = await connector.fetch_contracts()
    assert len(records) == 1
    assert records[0].business_number == "123456789"
    assert records[0].vendor_name == "Acme Corp"
    assert records[0].status == "active"

@pytest.mark.asyncio
@respx.mock
async def test_fetch_contracts_handles_http_error():
    respx.get("https://canadabuys.canada.ca/openapi/v1/contracts").mock(
        return_value=httpx.Response(503)
    )
    connector = CanadaBuysConnector(base_url="https://canadabuys.canada.ca/openapi/v1")
    records = await connector.fetch_contracts()
    assert records == []
