import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from portal.holder_agent import HolderSession

SAMPLE_CRED_JSON = json.dumps({
    "business_number": "123456789",
    "business_name": "Acme Corp",
    "supplier_status": "active",
    "issue_date": "2026-01-01",
    "expiry_date": "2027-01-01",
    "issuing_authority": "PSPC / DSTN",
})

async def test_activate_loads_credential():
    mock_store = MagicMock()
    mock_store.retrieve = AsyncMock(return_value=SAMPLE_CRED_JSON)
    session = HolderSession(did_key="did:key:zTest", credential_store=mock_store)
    await session.activate()
    assert session.is_active
    cred = session.get_credential()
    assert cred["business_number"] == "123456789"
    assert cred["supplier_status"] == "active"

async def test_deactivate_clears_credential():
    mock_store = MagicMock()
    mock_store.retrieve = AsyncMock(return_value=SAMPLE_CRED_JSON)
    session = HolderSession(did_key="did:key:zTest", credential_store=mock_store)
    await session.activate()
    session.deactivate()
    assert not session.is_active
    assert session.get_credential() is None

async def test_activate_with_no_credential_stays_inactive():
    mock_store = MagicMock()
    mock_store.retrieve = AsyncMock(return_value=None)
    session = HolderSession(did_key="did:key:zNoCred", credential_store=mock_store)
    await session.activate()
    assert not session.is_active
