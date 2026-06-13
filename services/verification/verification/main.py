# services/verification/verification/main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.config import settings
from shared.db import async_session_factory
from verification.verify import VerificationService

app = FastAPI(title="DSTN Verification API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])

@app.get("/api/verify/{business_number}")
async def verify(business_number: str):
    async with async_session_factory() as session:
        svc = VerificationService(
            session,
            stratos_url=settings.stratos_api_url,
            stratos_key=settings.stratos_api_key,
            rev_reg_id=settings.issuer_rev_reg_id,
        )
        return await svc.verify(business_number)

@app.get("/health")
async def health():
    return {"status": "ok"}
