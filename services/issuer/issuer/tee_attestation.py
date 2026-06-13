# services/issuer/issuer/tee_attestation.py
import base64
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

try:
    import stratos_tee
except ImportError:
    class _StratosTEEStub:
        def generate_attestation_quote(self, payload: bytes) -> bytes:
            logger.warning("TEE SDK not available — returning stub attestation quote")
            return b"STUB-ATTESTATION-QUOTE:" + payload[:32]

        def verify_quote(self, quote: bytes) -> bool:
            return quote.startswith(b"STUB-ATTESTATION-QUOTE:")

    stratos_tee = _StratosTEEStub()

@dataclass
class AttestationQuote:
    issuer_did: str
    quote_bytes: bytes
    generated_at: str = field(default="")

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()

class TEEAttestationService:
    def __init__(self, issuer_did: str):
        self.issuer_did = issuer_did

    async def generate_quote(self) -> AttestationQuote:
        payload = json.dumps({"issuer_did": self.issuer_did, "purpose": "dstn-credential-issuance"}).encode()
        quote_bytes = stratos_tee.generate_attestation_quote(payload)
        return AttestationQuote(issuer_did=self.issuer_did, quote_bytes=quote_bytes)

    async def verify(self, quote: AttestationQuote) -> bool:
        return stratos_tee.verify_quote(quote.quote_bytes)

    def as_did_service_entry(self, quote: AttestationQuote) -> dict:
        return {
            "id": f"{self.issuer_did}#tee-attestation",
            "type": "TEEAttestation",
            "serviceEndpoint": {
                "quote": base64.b64encode(quote.quote_bytes).decode(),
                "generated_at": quote.generated_at,
                "tee_type": "stratos-sgx",
            },
        }
