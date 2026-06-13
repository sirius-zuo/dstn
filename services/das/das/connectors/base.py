from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date

@dataclass
class ContractRecord:
    business_number: str
    vendor_name: str
    contract_date: date
    contract_end_date: date | None
    total_value: float
    status: str                 # "active" | "cancelled" | "closed"
    reference_number: str
    source: str = ""

class BaseConnector(ABC):
    @abstractmethod
    async def fetch_contracts(self) -> list[ContractRecord]:
        """Return all contract records from this data source. Return [] on error."""
