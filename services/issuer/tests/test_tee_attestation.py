# services/issuer/tests/test_tee_attestation.py
import pytest
from unittest.mock import patch
from issuer.tee_attestation import TEEAttestationService, AttestationQuote

@pytest.mark.asyncio
async def test_generate_quote_returns_attestation_object():
    with patch("issuer.tee_attestation.stratos_tee") as mock_tee:
        mock_tee.generate_attestation_quote.return_value = b"mock-quote-bytes"
        mock_tee.verify_quote.return_value = True
        svc = TEEAttestationService(issuer_did="did:stratos:issuer001")
        quote = await svc.generate_quote()
        assert isinstance(quote, AttestationQuote)
        assert len(quote.quote_bytes) > 0
        assert quote.issuer_did == "did:stratos:issuer001"

@pytest.mark.asyncio
async def test_verify_quote_returns_true_for_valid_quote():
    with patch("issuer.tee_attestation.stratos_tee") as mock_tee:
        mock_tee.verify_quote.return_value = True
        svc = TEEAttestationService(issuer_did="did:stratos:issuer001")
        quote = AttestationQuote(issuer_did="did:stratos:issuer001", quote_bytes=b"valid-quote")
        result = await svc.verify(quote)
        assert result is True

@pytest.mark.asyncio
async def test_attestation_embed_in_did_document():
    with patch("issuer.tee_attestation.stratos_tee") as mock_tee:
        mock_tee.generate_attestation_quote.return_value = b"quote-bytes"
        svc = TEEAttestationService(issuer_did="did:stratos:issuer001")
        quote = await svc.generate_quote()
        service_entry = svc.as_did_service_entry(quote)
        assert service_entry["type"] == "TEEAttestation"
        assert "quote" in service_entry["serviceEndpoint"]
