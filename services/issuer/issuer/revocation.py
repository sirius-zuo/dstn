import logging
from issuer.stratos_client import StratosClient

logger = logging.getLogger(__name__)

class RevocationManager:
    def __init__(self, api_url: str, api_key: str, rev_reg_id: str):
        self.client = StratosClient(api_url=api_url, api_key=api_key)
        self.rev_reg_id = rev_reg_id

    async def revoke(self, cred_rev_id: str) -> bool:
        try:
            await self.client.update_revocation_registry(
                rev_reg_id=self.rev_reg_id,
                revoked_indices=[int(cred_rev_id)],
            )
            return True
        except Exception as exc:
            logger.error("Revocation failed for cred_rev_id=%s: %s", cred_rev_id, exc)
            return False

    async def is_revoked(self, cred_rev_id: str) -> bool:
        return await self.client.get_revocation_status(self.rev_reg_id, cred_rev_id)
