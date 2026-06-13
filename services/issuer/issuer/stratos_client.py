# services/issuer/issuer/stratos_client.py
import logging
from dataclasses import dataclass, field
import httpx

logger = logging.getLogger(__name__)

@dataclass
class DIDDocument:
    id: str
    verification_method: list[dict] = field(default_factory=list)

class StratosClient:
    """REST client for the Stratos blockchain DID registry and AnonCreds anchoring.

    Endpoint paths follow the expected Stratos REST API convention.
    Update paths if the actual Stratos SDK documentation differs.
    """

    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url.rstrip("/")
        self.headers = {"x-api-key": api_key, "Content-Type": "application/json"}

    def _did_identifier(self, did: str) -> str:
        return did.removeprefix("did:stratos:")

    async def resolve_did(self, did: str) -> DIDDocument:
        identifier = self._did_identifier(did)
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{self.api_url}/did/{identifier}", headers=self.headers)
            r.raise_for_status()
            data = r.json()
        return DIDDocument(
            id=data["id"],
            verification_method=data.get("verificationMethod", []),
        )

    async def register_did(self, seed: str) -> str:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                f"{self.api_url}/did", json={"seed": seed}, headers=self.headers
            )
            r.raise_for_status()
            return r.json()["did"]

    async def anchor_schema(self, issuer_did: str, name: str, version: str, attr_names: list[str]) -> str:
        payload = {
            "issuer_did": issuer_did,
            "name": name,
            "version": version,
            "attr_names": attr_names,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(f"{self.api_url}/anoncreds/schema", json=payload, headers=self.headers)
            r.raise_for_status()
            return r.json()["schema_id"]

    async def anchor_cred_def(self, issuer_did: str, schema_id: str, tag: str = "default") -> str:
        payload = {"issuer_did": issuer_did, "schema_id": schema_id, "tag": tag, "support_revocation": True}
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(f"{self.api_url}/anoncreds/credential-definition", json=payload, headers=self.headers)
            r.raise_for_status()
            return r.json()["cred_def_id"]

    async def create_revocation_registry(self, cred_def_id: str, max_cred_num: int = 32767) -> str:
        payload = {"cred_def_id": cred_def_id, "max_cred_num": max_cred_num}
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(f"{self.api_url}/anoncreds/revocation-registry", json=payload, headers=self.headers)
            r.raise_for_status()
            return r.json()["rev_reg_id"]

    async def update_revocation_registry(self, rev_reg_id: str, revoked_indices: list[int]) -> None:
        payload = {"rev_reg_id": rev_reg_id, "revoked": revoked_indices}
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.patch(f"{self.api_url}/anoncreds/revocation-registry", json=payload, headers=self.headers)
            r.raise_for_status()

    async def get_revocation_status(self, rev_reg_id: str, cred_rev_id: str) -> bool:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{self.api_url}/anoncreds/revocation-registry/{rev_reg_id}/status",
                params={"cred_rev_id": cred_rev_id},
                headers=self.headers,
            )
            r.raise_for_status()
            return r.json().get("revoked", False)
