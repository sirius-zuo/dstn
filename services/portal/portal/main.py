# services/portal/portal/main.py
import json
import logging
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
from shared.config import settings
from shared.db import async_session_factory
from portal.passkey import PasskeyManager
from portal.passkey_registry import PasskeyRegistry
from portal.tee_credential_store import TEECredentialStore as CredentialStore
from portal.holder_agent import HolderSession
from portal.session import create_session_token, decode_session_token
from webauthn import verify_registration_response, verify_authentication_response
from webauthn.helpers.structs import AuthenticatorTransport

app = FastAPI(title="DSTN Supplier Portal")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Cache-Control"] = "no-store"
        return response

app.add_middleware(SecurityHeadersMiddleware)
_passkey_mgr = PasskeyManager(rp_id=settings.portal_rp_id, rp_name=settings.portal_rp_name, origin=settings.portal_origin)

class RegistrationCompleteRequest(BaseModel):
    challenge: str
    credential: dict

class AuthCompleteRequest(BaseModel):
    challenge: str
    assertion: dict

class HolderReceiveRequest(BaseModel):
    did_key: str
    credential_json: str
    cred_ex_id: str | None = None

def _require_session(authorization: str = Header(...)) -> dict:
    try:
        token = authorization.removeprefix("Bearer ")
        return decode_session_token(token, settings.portal_secret_key)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

@app.get("/passkey/register/begin")
async def register_begin(business_number: str):
    options, challenge = _passkey_mgr.begin_registration(business_number, business_number)
    return {"options": options.model_dump() if hasattr(options, "model_dump") else options.__dict__, "challenge": challenge}

@app.post("/passkey/register/complete")
async def register_complete(body: RegistrationCompleteRequest):
    business_number = _passkey_mgr.consume_challenge(body.challenge)
    if business_number is None:
        raise HTTPException(400, "Invalid or expired challenge")
    try:
        verification = verify_registration_response(
            credential=body.credential,
            expected_challenge=body.challenge.encode(),
            expected_rp_id=settings.portal_rp_id,
            expected_origin=settings.portal_origin,
        )
    except Exception as exc:
        raise HTTPException(400, f"Registration verification failed: {exc}")
    async with async_session_factory() as session:
        registry = PasskeyRegistry(session)
        did_key = await registry.register(
            business_number=business_number,
            credential_id=verification.credential_id,
            public_key_cose=verification.credential_public_key,
            sign_count=verification.sign_count,
        )
    token = create_session_token(business_number, did_key, settings.portal_secret_key)
    return {"session_token": token, "did_key": did_key}

@app.get("/passkey/auth/begin")
async def auth_begin():
    options, challenge = _passkey_mgr.begin_authentication()
    return {"options": options.model_dump() if hasattr(options, "model_dump") else options.__dict__, "challenge": challenge}

@app.post("/passkey/auth/complete")
async def auth_complete(body: AuthCompleteRequest):
    if _passkey_mgr.consume_challenge(body.challenge) is None:
        raise HTTPException(400, "Invalid or expired challenge")
    credential_id_bytes =bytes(body.assertion.get("rawId", []))
    async with async_session_factory() as session:
        registry = PasskeyRegistry(session)
        passkey_record = await registry.lookup_by_credential_id(credential_id_bytes)
        if passkey_record is None:
            raise HTTPException(401, "Passkey not registered")
        try:
            verification = verify_authentication_response(
                credential=body.assertion,
                expected_challenge=body.challenge.encode(),
                expected_rp_id=settings.portal_rp_id,
                expected_origin=settings.portal_origin,
                credential_public_key=passkey_record.public_key_cose,
                credential_current_sign_count=passkey_record.sign_count,
            )
        except Exception as exc:
            raise HTTPException(401, f"Authentication failed: {exc}")
        await registry.update_sign_count(credential_id_bytes, verification.new_sign_count)
        token = create_session_token(passkey_record.business_number, passkey_record.did_key, settings.portal_secret_key)
    return {"session_token": token, "did_key": passkey_record.did_key}

@app.get("/credential/status")
async def credential_status(session_data: dict = Depends(_require_session)):
    did_key = session_data["did_key"]
    async with async_session_factory() as db_session:
        store = CredentialStore(db_session, settings.portal_secret_key)
        holder = HolderSession(did_key, store)
        await holder.activate()
        cred = holder.get_credential()
        holder.deactivate()
    if cred is None:
        return {"status": "pending", "did_key": did_key}
    return {"status": cred.get("supplier_status", "unknown"), "credential": cred, "did_key": did_key}

@app.post("/holder/receive")
async def holder_receive(body: HolderReceiveRequest):
    async with async_session_factory() as db_session:
        store = CredentialStore(db_session, settings.portal_secret_key)
        await store.store(body.did_key, body.credential_json, body.cred_ex_id)
    return {"result": "stored"}
