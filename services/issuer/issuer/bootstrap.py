"""Run once to anchor schema + cred def on Stratos. Outputs IDs to set in .env."""
import asyncio
import os
from issuer.schema import SchemaManager

async def main():
    api_url = os.environ["STRATOS_API_URL"]
    api_key = os.environ["STRATOS_API_KEY"]
    issuer_did = os.environ.get("ISSUER_DID")
    if not issuer_did:
        from issuer.stratos_client import StratosClient
        seed = os.environ["STRATOS_DID_SEED"]
        client = StratosClient(api_url=api_url, api_key=api_key)
        issuer_did = await client.register_did(seed=seed)
        print(f"ISSUER_DID={issuer_did}")

    manager = SchemaManager(api_url=api_url, api_key=api_key, issuer_did=issuer_did)
    ids = await manager.ensure_schema_and_cred_def()
    print(f"ISSUER_SCHEMA_ID={ids['schema_id']}")
    print(f"ISSUER_CRED_DEF_ID={ids['cred_def_id']}")
    print(f"ISSUER_REV_REG_ID={ids['rev_reg_id']}")
    print("Copy these values into your .env file.")

if __name__ == "__main__":
    asyncio.run(main())
