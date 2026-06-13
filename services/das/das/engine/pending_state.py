import json
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from shared.models import PasskeyRecord, SupplierRecord, SupplierStatus
from das.engine.status_derivation import DerivedStatus


class PendingStateStore:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(self, derived: DerivedStatus) -> SupplierRecord:
        existing = await self.session.get(SupplierRecord, derived.business_number)
        now = datetime.now(timezone.utc)

        if existing is None:
            passkey = (await self.session.execute(
                select(PasskeyRecord).where(PasskeyRecord.business_number == derived.business_number)
            )).scalar_one_or_none()
            existing = SupplierRecord(
                business_number=derived.business_number,
                business_name=derived.business_name,
                status=SupplierStatus.ACTIVE if (passkey and derived.status == "active") else SupplierStatus.PENDING_REGISTRATION,
                data_sources=json.dumps(derived.data_sources),
                last_synced_at=now,
                credential_issued=False,
                did_key=passkey.did_key if passkey else None,
            )
            self.session.add(existing)
        else:
            existing.business_name = derived.business_name
            existing.data_sources = json.dumps(derived.data_sources)
            existing.last_synced_at = now

            if derived.status == "revoked":
                existing.status = SupplierStatus.REVOKED
            elif existing.did_key and existing.status == SupplierStatus.PENDING_REGISTRATION:
                # Passkey was registered while status was pending — promote to active
                existing.status = SupplierStatus.ACTIVE
            # If already ACTIVE or REVOKED with a passkey, leave status unchanged here;
            # the Credential Trigger handles status-change events.

        await self.session.commit()
        return existing
