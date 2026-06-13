import pytest
from portal.session import create_session_token, decode_session_token

SECRET = "test-secret-32-chars-exactly!!!!"

def test_create_and_decode_session_token():
    token = create_session_token("123456789", "did:key:zTest", SECRET)
    payload = decode_session_token(token, SECRET)
    assert payload["sub"] == "123456789"
    assert payload["did_key"] == "did:key:zTest"

def test_decode_invalid_token_raises():
    import pytest, jwt
    with pytest.raises(Exception):
        decode_session_token("not-a-token", SECRET)
