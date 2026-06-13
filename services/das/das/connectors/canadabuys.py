import logging
from datetime import date
import httpx
from das.connectors.base import BaseConnector, ContractRecord

logger = logging.getLogger(__name__)

class CanadaBuysConnector(BaseConnector):
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def fetch_contracts(self) -> list[ContractRecord]:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.get(f"{self.base_url}/contracts")
                r.raise_for_status()
                data = r.json()
        except Exception as exc:
            logger.warning("CanadaBuys fetch failed: %s", exc)
            return []

        records = []
        for item in data.get("contracts", []):
            try:
                records.append(ContractRecord(
                    business_number=item["business_number"],
                    vendor_name=item["vendor_name"],
                    contract_date=date.fromisoformat(item["contract_date"]),
                    contract_end_date=date.fromisoformat(item["contract_period_end"]) if item.get("contract_period_end") else None,
                    total_value=float(item.get("total_value", 0)),
                    status=item.get("status", "active"),
                    reference_number=item["reference_number"],
                    source="canadabuys",
                ))
            except (KeyError, ValueError) as exc:
                logger.warning("Skipping malformed CanadaBuys record: %s", exc)
        return records
