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

    async def _get_or_create_connection(self, holder_did: str) -> str | None:
        """Look up ACA-Py connection record for this holder DID. Returns connection_id or None."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    f"{self.admin_url}/connections",
                    params={"their_did": holder_did},
                    headers=self.headers,
                )
                r.raise_for_status()
                results = r.json().get("results", [])
                if results:
                    return results[0]["connection_id"]
                logger.warning("No ACA-Py connection found for holder DID %s", holder_did)
                return None
        except Exception as exc:
            logger.error("Connection lookup failed for %s: %s", holder_did, exc)
            return None

    async def issue(self, business_number: str, business_name: str, holder_did: str) -> str | None:
        from shared.config import settings
        from datetime import date

        connection_id = await self._get_or_create_connection(holder_did)
        if not connection_id:
            return None

        payload = {
            "auto_remove": False,
            "connection_id": connection_id,
            "cred_def_id": settings.issuer_cred_def_id,
            "credential_preview": {
                "@type": "issue-credential/2.0/credential-preview",
                "attributes": [
                    {"name": "business_number", "value": business_number},
                    {"name": "business_name", "value": business_name},
                    {"name": "supplier_status", "value": "active"},
                    {"name": "issue_date", "value": date.today().isoformat()},
                    {"name": "expiry_date", "value": str(date.today().year + 1) + "-01-01"},
                    {"name": "issuing_authority", "value": "PSPC / DSTN"},
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
            logger.error("Credential issuance failed for %s: %s", business_number, exc)
            return None

    async def revoke(self, cred_ex_id: str, rev_reg_id: str = "") -> bool:
        from shared.config import settings
        actual_rev_reg_id = rev_reg_id or settings.issuer_rev_reg_id
        payload = {"cred_ex_id": cred_ex_id, "rev_reg_id": actual_rev_reg_id, "publish": True}
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
