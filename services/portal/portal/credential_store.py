# services/portal/portal/credential_store.py
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.hashes import SHA256
from sqlalchemy.ext.asyncio import AsyncSession
from shared.models import EncryptedCredential
from datetime import datetime, timezone

class CredentialStore:
    def __init__(self, session: AsyncSession, server_secret: str):
        self.session = session
        self._server_secret = server_secret.encode()

    def _derive_key(self, did_key: str) -> bytes:
        hkdf = HKDF(algorithm=SHA256(), length=32, salt=None, info=did_key.encode())
        return hkdf.derive(self._server_secret)

    def _encrypt(self, did_key: str, plaintext: bytes) -> tuple[bytes, bytes]:
        key = self._derive_key(did_key)
        nonce = os.urandom(12)
        ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)
        return ciphertext, nonce

    def _decrypt(self, did_key: str, ciphertext: bytes, nonce: bytes) -> bytes:
        key = self._derive_key(did_key)
        return AESGCM(key).decrypt(nonce, ciphertext, None)

    async def store(self, did_key: str, credential_json: str, cred_ex_id: str | None = None) -> None:
        ciphertext, nonce = self._encrypt(did_key, credential_json.encode())
        existing = await self.session.get(EncryptedCredential, did_key)
        now = datetime.now(timezone.utc)
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
        plaintext = self._decrypt(did_key, record.ciphertext, record.nonce)
        return plaintext.decode()
