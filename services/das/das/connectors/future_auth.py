# services/das/das/connectors/future_auth.py
import logging
from das.connectors.base import BaseConnector, ContractRecord

logger = logging.getLogger(__name__)

class FutureAuthConnector(BaseConnector):
    """Pluggable adapter for the future authoritative GoC data source (per AMD002).
    Replace this implementation when the source is determined."""

    async def fetch_contracts(self) -> list[ContractRecord]:
        logger.info("FutureAuthConnector: no source configured — returning empty")
        return []
