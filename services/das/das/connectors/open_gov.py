# services/das/das/connectors/open_gov.py
import csv
import io
import logging
from datetime import date
import httpx
from das.connectors.base import BaseConnector, ContractRecord

logger = logging.getLogger(__name__)

class OpenGovConnector(BaseConnector):
    def __init__(self, dataset_url: str):
        self.dataset_url = dataset_url

    async def fetch_contracts(self) -> list[ContractRecord]:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.get(self.dataset_url)
                r.raise_for_status()
                text = r.text
        except Exception as exc:
            logger.warning("Open Gov fetch failed: %s", exc)
            return []

        records = []
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            try:
                end_date_raw = row.get("contract_period_end", "").strip()
                records.append(ContractRecord(
                    business_number=row.get("vendor_business_number", "").strip(),
                    vendor_name=row["vendor_name"].strip(),
                    contract_date=date.fromisoformat(row["contract_date"].strip()),
                    contract_end_date=date.fromisoformat(end_date_raw) if end_date_raw else None,
                    total_value=float(row.get("contract_value", 0) or 0),
                    status=row.get("status", "active").strip(),
                    reference_number=row["reference_number"].strip(),
                    source="open_gov",
                ))
            except (KeyError, ValueError) as exc:
                logger.warning("Skipping malformed Open Gov row: %s", exc)
        return records
