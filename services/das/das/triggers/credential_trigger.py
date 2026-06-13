import logging
import httpx

logger = logging.getLogger(__name__)


class TriggerEvent:
    ISSUE = "issue"
    REVOKE = "revoke"


class CredentialTrigger:
    """Calls the Aries Issuer Agent admin API to issue or revoke credentials.
    Populated with full request body in Part 2 once schema/cred_def IDs are known."""

    def __init__(self, admin_url: str, api_key: str):
        self.admin_url = admin_url.rstrip("/")
        self.headers = {"x-api-key": api_key}

    async def issue(self, business_number: str, business_name: str, holder_did: str) -> str | None:
        """Request credential issuance. Returns cred_ex_id or None on failure."""
        payload = {
            "auto_remove": False,
            "comment": f"DSTN credential for {business_number}",
            "connection_id": "",          # filled in Part 2 with TEE Holder connection ID
            "cred_def_id": "",            # filled in Part 2 once anchored on Stratos
            "credential_preview": {
                "@type": "issue-credential/2.0/credential-preview",
                "attributes": [
                    {"name": "business_number", "value": business_number},
                    {"name": "business_name", "value": business_name},
                    {"name": "holder_did", "value": holder_did},
                    {"name": "supplier_status", "value": "active"},
                ],
            },
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(
                    f"{self.admin_url}/issue-credential-2.0/send",
                    json=payload,
                    headers=self.headers,
                )
                r.raise_for_status()
                return r.json().get("cred_ex_id")
        except Exception as exc:
            logger.error("Credential issuance trigger failed for %s: %s", business_number, exc)
            return None

    async def revoke(self, cred_ex_id: str, rev_reg_id: str) -> bool:
        """Request credential revocation. Returns True on success."""
        payload = {"cred_ex_id": cred_ex_id, "rev_reg_id": rev_reg_id, "publish": True}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(
                    f"{self.admin_url}/revocation/revoke",
                    json=payload,
                    headers=self.headers,
                )
                r.raise_for_status()
                return True
        except Exception as exc:
            logger.error("Credential revocation trigger failed for %s: %s", cred_ex_id, exc)
            return False
