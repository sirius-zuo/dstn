# services/verification/verification/verify.py
import httpx
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from shared.models import PasskeyRecord, EncryptedCredential

logger = logging.getLogger(__name__)

class VerificationService:
    def __init__(self, session: AsyncSession, stratos_url: str, stratos_key: str, rev_reg_id: str):
        self.session = session
        self.stratos_url = stratos_url.rstrip("/")
        self.stratos_key = stratos_key
        self.rev_reg_id = rev_reg_id

    async def verify(self, business_number: str) -> dict:
        result = await self.session.execute(
            select(PasskeyRecord).where(PasskeyRecord.business_number == business_number)
        )
        passkey = result.scalar_one_or_none()
        if passkey is None:
            return {"business_number": business_number, "status": "not_found", "revoked": None}

        cred_record = await self.session.get(EncryptedCredential, passkey.did_key)
        if cred_record is None:
            return {"business_number": business_number, "status": "pending", "revoked": None}

        revoked = await self._check_revocation(cred_record.cred_ex_id or "0")

        return {
            "business_number": business_number,
            "did_key": passkey.did_key,
            "status": "revoked" if revoked else "active",
            "revoked": revoked,
            "credential_issued_at": cred_record.updated_at.isoformat() if cred_record.updated_at else None,
            "issuing_authority": "PSPC / DSTN",
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _check_revocation(self, cred_ex_id: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(
                    f"{self.stratos_url}/anoncreds/revocation-registry/{self.rev_reg_id}/status",
                    params={"cred_rev_id": cred_ex_id},
                    headers={"x-api-key": self.stratos_key},
                )
                r.raise_for_status()
                return r.json().get("revoked", False)
        except Exception as exc:
            logger.warning("Revocation check failed: %s — treating as not revoked", exc)
            return False
