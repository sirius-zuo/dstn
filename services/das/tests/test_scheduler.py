import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from das.scheduler import run_sync_cycle

async def test_sync_cycle_calls_all_connectors():
    mock_cb_records = [MagicMock(business_number="111", vendor_name="Corp A", status="active")]
    mock_og_records = []

    with patch("das.scheduler.CanadaBuysConnector") as MockCB, \
         patch("das.scheduler.OpenGovConnector") as MockOG, \
         patch("das.scheduler.FutureAuthConnector") as MockFA, \
         patch("das.scheduler.StatusDerivationEngine") as MockEngine, \
         patch("das.scheduler.async_session_factory") as MockSession:

        MockCB.return_value.fetch_contracts = AsyncMock(return_value=mock_cb_records)
        MockOG.return_value.fetch_contracts = AsyncMock(return_value=mock_og_records)
        MockFA.return_value.fetch_contracts = AsyncMock(return_value=[])
        MockEngine.return_value.derive = MagicMock(return_value={})
        MockSession.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

        await run_sync_cycle()

        MockCB.return_value.fetch_contracts.assert_called_once()
        MockOG.return_value.fetch_contracts.assert_called_once()
