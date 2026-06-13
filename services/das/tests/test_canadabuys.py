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


@pytest.mark.asyncio
@respx.mock
async def test_fetch_contracts_skips_malformed_keeps_valid():
    """One bad record (missing required field) should not drop the good one."""
    respx.get("https://canadabuys.canada.ca/openapi/v1/contracts").mock(
        return_value=httpx.Response(200, json={
            "contracts": [
                {
                    # missing vendor_name — required field
                    "business_number": "111111111",
                    "contract_date": "2024-01-01",
                    "reference_number": "CB-2024-BAD",
                },
                {
                    "vendor_name": "Good Corp",
                    "business_number": "222222222",
                    "contract_date": "2024-03-15",
                    "contract_period_end": "2025-03-14",
                    "total_value": 50000.0,
                    "status": "active",
                    "reference_number": "CB-2024-GOOD",
                },
            ]
        })
    )
    connector = CanadaBuysConnector(base_url="https://canadabuys.canada.ca/openapi/v1")
    records = await connector.fetch_contracts()
    assert len(records) == 1
    assert records[0].business_number == "222222222"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_contracts_skips_invalid_date():
    """A record with an unparseable contract_date is skipped."""
    respx.get("https://canadabuys.canada.ca/openapi/v1/contracts").mock(
        return_value=httpx.Response(200, json={
            "contracts": [
                {
                    "vendor_name": "Bad Date Corp",
                    "business_number": "333333333",
                    "contract_date": "not-a-date",
                    "reference_number": "CB-2024-BADDATE",
                }
            ]
        })
    )
    connector = CanadaBuysConnector(base_url="https://canadabuys.canada.ca/openapi/v1")
    records = await connector.fetch_contracts()
    assert records == []


@pytest.mark.asyncio
@respx.mock
async def test_fetch_contracts_skips_missing_business_number():
    """A record without business_number is skipped."""
    respx.get("https://canadabuys.canada.ca/openapi/v1/contracts").mock(
        return_value=httpx.Response(200, json={
            "contracts": [
                {
                    "vendor_name": "No BN Corp",
                    # business_number absent
                    "contract_date": "2024-03-15",
                    "reference_number": "CB-2024-NOBN",
                }
            ]
        })
    )
    connector = CanadaBuysConnector(base_url="https://canadabuys.canada.ca/openapi/v1")
    records = await connector.fetch_contracts()
    assert records == []
