# services/portal/portal/passkey_registry.py
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from shared.models import PasskeyRecord, SupplierRecord, SupplierStatus
from portal.did_key import derive_did_key_from_cose

logger = logging.getLogger(__name__)

class PasskeyRegistry:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def register(self, business_number: str, credential_id: bytes, public_key_cose: bytes, sign_count: int) -> str:
        did_key = derive_did_key_from_cose(public_key_cose)
        existing = await self.session.get(PasskeyRecord, credential_id)
        if existing:
            existing.sign_count = sign_count
            existing.did_key = did_key
            existing.public_key_cose = public_key_cose
        else:
            self.session.add(PasskeyRecord(
                credential_id=credential_id,
                business_number=business_number,
                public_key_cose=public_key_cose,
                did_key=did_key,
                sign_count=sign_count,
            ))
        supplier = await self.session.get(SupplierRecord, business_number)
        if supplier:
            supplier.did_key = did_key
            if supplier.status == SupplierStatus.PENDING_REGISTRATION:
                supplier.status = SupplierStatus.ACTIVE
        await self.session.commit()
        return did_key

    async def lookup_by_credential_id(self, credential_id: bytes) -> PasskeyRecord | None:
        return await self.session.get(PasskeyRecord, credential_id)

    async def update_sign_count(self, credential_id: bytes, new_sign_count: int) -> None:
        record = await self.session.get(PasskeyRecord, credential_id)
        if record:
            record.sign_count = new_sign_count
            await self.session.commit()
