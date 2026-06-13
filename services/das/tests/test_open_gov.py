# services/das/tests/test_open_gov.py
import pytest
import respx
import httpx
from das.connectors.open_gov import OpenGovConnector

SAMPLE_CSV = (
    "reference_number,vendor_name,vendor_business_number,contract_date,"
    "contract_period_end,contract_value,status\r\n"
    "OG-2024-001,Widgets Ltd,987654321,2024-01-10,2025-01-09,50000.0,active\r\n"
    "OG-2024-002,No BN Corp,,2024-02-20,,25000.0,active\r\n"
)

DATASET_URL = "https://open.canada.ca/data/en/datastore/dump/d8f85d91-7dec-4fd1-8055-483b77225d8b"

@pytest.mark.asyncio
@respx.mock
async def test_fetch_contracts_parses_csv():
    respx.get(DATASET_URL).mock(return_value=httpx.Response(200, text=SAMPLE_CSV))
    connector = OpenGovConnector(dataset_url=DATASET_URL)
    records = await connector.fetch_contracts()
    assert len(records) == 2
    assert records[0].business_number == "987654321"
    assert records[0].vendor_name == "Widgets Ltd"
    assert records[1].business_number == ""   # no BN in source data

@pytest.mark.asyncio
@respx.mock
async def test_fetch_contracts_handles_error():
    respx.get(DATASET_URL).mock(return_value=httpx.Response(404))
    connector = OpenGovConnector(dataset_url=DATASET_URL)
    records = await connector.fetch_contracts()
    assert records == []
