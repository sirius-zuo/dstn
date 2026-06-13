import pytest
from unittest.mock import MagicMock, patch
from portal.passkey import PasskeyManager

def test_begin_registration_returns_options_and_challenge():
    manager = PasskeyManager(rp_id="localhost", rp_name="DSTN", origin="http://localhost:3000")
    options, challenge = manager.begin_registration(business_number="123456789", user_display_name="Acme Corp")
    assert options is not None
    assert len(challenge) > 0

def test_begin_authentication_returns_options_and_challenge():
    manager = PasskeyManager(rp_id="localhost", rp_name="DSTN", origin="http://localhost:3000")
    options, challenge = manager.begin_authentication()
    assert options is not None
    assert len(challenge) > 0

def test_challenge_stored_after_begin_registration():
    manager = PasskeyManager(rp_id="localhost", rp_name="DSTN", origin="http://localhost:3000")
    _, challenge = manager.begin_registration("999888777", "Test Corp")
    assert manager.has_pending_challenge(challenge)
