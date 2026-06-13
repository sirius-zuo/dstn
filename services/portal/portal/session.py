# services/portal/portal/session.py
import jwt
from datetime import datetime, timezone, timedelta

SESSION_EXPIRY_HOURS = 8

def create_session_token(business_number: str, did_key: str, secret: str) -> str:
    payload = {
        "sub": business_number,
        "did_key": did_key,
        "exp": datetime.now(timezone.utc) + timedelta(hours=SESSION_EXPIRY_HOURS),
    }
    return jwt.encode(payload, secret, algorithm="HS256")

def decode_session_token(token: str, secret: str) -> dict:
    return jwt.decode(token, secret, algorithms=["HS256"], options={"require": ["exp", "sub"]})
