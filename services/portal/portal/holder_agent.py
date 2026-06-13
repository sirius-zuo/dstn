# services/portal/portal/holder_agent.py
import json
import logging

logger = logging.getLogger(__name__)

class HolderSession:
    """Session-scoped holder agent. Activate on passkey auth, deactivate at session end.

    In Part 5: wrap to run inside Stratos TEE with hardware-attested key derivation.
    The interface (activate / deactivate / get_credential) stays identical.
    """

    def __init__(self, did_key: str, credential_store):
        self.did_key = did_key
        self._store = credential_store
        self._credential: dict | None = None

    @property
    def is_active(self) -> bool:
        return self._credential is not None

    async def activate(self) -> None:
        cred_json = await self._store.retrieve(self.did_key)
        if cred_json is None:
            logger.info("No stored credential for %s — session inactive", self.did_key)
            return
        self._credential = json.loads(cred_json)

    def deactivate(self) -> None:
        self._credential = None
        logger.info("Holder session deactivated for %s — key material cleared", self.did_key)

    def get_credential(self) -> dict | None:
        return self._credential
