from issuer.stratos_client import StratosClient

DSTN_SCHEMA_NAME = "GoCSupplierCredential"
DSTN_SCHEMA_VERSION = "1.0"
DSTN_SCHEMA_ATTRS = [
    "business_number",
    "business_name",
    "supplier_status",
    "issue_date",
    "expiry_date",
    "issuing_authority",
]

class SchemaManager:
    def __init__(self, api_url: str, api_key: str, issuer_did: str):
        self.client = StratosClient(api_url=api_url, api_key=api_key)
        self.issuer_did = issuer_did

    async def ensure_schema_and_cred_def(self) -> dict:
        """Anchor schema, cred def, and revocation registry. Returns dict with IDs."""
        schema_id = await self.client.anchor_schema(
            issuer_did=self.issuer_did,
            name=DSTN_SCHEMA_NAME,
            version=DSTN_SCHEMA_VERSION,
            attr_names=DSTN_SCHEMA_ATTRS,
        )
        cred_def_id = await self.client.anchor_cred_def(
            issuer_did=self.issuer_did,
            schema_id=schema_id,
            tag="default",
        )
        rev_reg_id = await self.client.create_revocation_registry(cred_def_id=cred_def_id)
        return {"schema_id": schema_id, "cred_def_id": cred_def_id, "rev_reg_id": rev_reg_id}
