# services/portal/portal/tee_credential_store.py
import os
import logging
from datetime import datetime, timezone
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy.ext.asyncio import AsyncSession
from shared.models import EncryptedCredential

logger = logging.getLogger(__name__)

try:
    import stratos_tee

    def _derive_tee_key(did_key: str) -> bytes:
        return stratos_tee.seal_key(context=did_key.encode())

except ImportError:
    logger.info("Stratos TEE SDK not available — using deterministic key derivation stub")
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives.hashes import SHA256

    _TEE_STUB_SECRET = os.environ.get("PORTAL_SECRET_KEY", "stub-secret-32-chars-exactly!!!").encode()

    def _derive_tee_key(did_key: str) -> bytes:
        hkdf = HKDF(algorithm=SHA256(), length=32, salt=b"tee-stub", info=did_key.encode())
        return hkdf.derive(_TEE_STUB_SECRET)


class TEECredentialStore:
    """CredentialStore backed by Stratos TEE key sealing.

    Drop-in replacement for CredentialStore (same store/retrieve interface).
    In production: keys are sealed to the TEE enclave identity.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def store(self, did_key: str, credential_json: str, cred_ex_id: str | None = None) -> None:
        key = _derive_tee_key(did_key)
        nonce = os.urandom(12)
        ciphertext = AESGCM(key).encrypt(nonce, credential_json.encode(), None)
        now = datetime.now(timezone.utc)
        existing = await self.session.get(EncryptedCredential, did_key)
        if existing:
            existing.ciphertext = ciphertext
            existing.nonce = nonce
            existing.cred_ex_id = cred_ex_id
            existing.updated_at = now
        else:
            self.session.add(EncryptedCredential(
                did_key=did_key, ciphertext=ciphertext, nonce=nonce,
                cred_ex_id=cred_ex_id, updated_at=now,
            ))
        await self.session.commit()

    async def retrieve(self, did_key: str) -> str | None:
        record = await self.session.get(EncryptedCredential, did_key)
        if not record:
            return None
        key = _derive_tee_key(did_key)
        return AESGCM(key).decrypt(record.nonce, record.ciphertext, None).decode()
