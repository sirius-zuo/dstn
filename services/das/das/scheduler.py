import logging
import time
from prometheus_client import Gauge
from shared.config import settings

_LAST_SYNC_TIMESTAMP = Gauge("dstn_last_sync_timestamp", "Unix timestamp of last successful DAS sync")
from shared.db import async_session_factory
from das.connectors.canadabuys import CanadaBuysConnector
from das.connectors.open_gov import OpenGovConnector
from das.connectors.future_auth import FutureAuthConnector
from das.engine.status_derivation import StatusDerivationEngine
from das.engine.pending_state import PendingStateStore
from das.triggers.credential_trigger import CredentialTrigger

logger = logging.getLogger(__name__)

async def run_sync_cycle() -> None:
    logger.info("Starting data sync cycle")
    cb = CanadaBuysConnector(base_url=settings.canadabuys_base_url)
    og = OpenGovConnector(dataset_url=settings.open_gov_dataset_url)
    fa = FutureAuthConnector()

    all_records = []
    for connector in (cb, og, fa):
        records = await connector.fetch_contracts()
        all_records.extend(records)

    logger.info("Fetched %d total contract records", len(all_records))

    engine = StatusDerivationEngine()
    derived = engine.derive(all_records)
    logger.info("Derived status for %d suppliers", len(derived))

    trigger = CredentialTrigger(
        admin_url=settings.issuer_agent_admin_url,
        api_key=settings.issuer_agent_api_key,
    )

    async with async_session_factory() as session:
        store = PendingStateStore(session)
        for derived_status in derived.values():
            record = await store.upsert(derived_status)
            # Trigger issuance for active suppliers with a registered passkey
            if derived_status.status == "active" and record.did_key and not record.credential_issued:
                cred_ex_id = await trigger.issue(
                    record.business_number,
                    record.business_name,
                    record.did_key,
                )
                if cred_ex_id:
                    record.credential_issued = True
                    record.credential_id = cred_ex_id
                    await session.commit()
            elif derived_status.status == "revoked" and record.credential_issued and record.credential_id:
                await trigger.revoke(record.credential_id, rev_reg_id="")  # rev_reg_id filled in Part 2
    _LAST_SYNC_TIMESTAMP.set(time.time())
    logger.info("Sync cycle complete")
