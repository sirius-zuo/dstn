# services/issuer/issuer/tee_key_backend.py
"""ACA-Py wallet key backend using Stratos TEE hardware key storage.

To enable: set wallet-key-backend: issuer.tee_key_backend.StratosTEEKeyBackend
in acapy-config.yml. Falls back to software wallet when TEE SDK is absent.
"""
import logging

logger = logging.getLogger(__name__)

try:
    import stratos_tee

    class StratosTEEKeyBackend:
        async def create_key(self, key_type: str) -> str:
            key_id = stratos_tee.create_key(key_type=key_type)
            logger.info("Created TEE-resident key: %s (%s)", key_id, key_type)
            return key_id

        async def sign(self, key_id: str, message: bytes) -> bytes:
            return stratos_tee.sign(key_id=key_id, message=message)

        async def verify(self, key_id: str, message: bytes, signature: bytes) -> bool:
            return stratos_tee.verify(key_id=key_id, message=message, signature=signature)

except ImportError:
    logger.info("Stratos TEE SDK not available — TEE key backend disabled (using software wallet)")
    StratosTEEKeyBackend = None
