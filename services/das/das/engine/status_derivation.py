import re
from dataclasses import dataclass
from das.connectors.base import ContractRecord


@dataclass
class DerivedStatus:
    business_number: str
    business_name: str
    status: str                 # "active" | "revoked"
    data_sources: list[str]


def _normalize_name(name: str) -> str:
    return re.sub(r"\s+", "_", name.strip().lower())


class StatusDerivationEngine:
    def derive(self, records: list[ContractRecord]) -> dict[str, DerivedStatus]:
        """Return a dict keyed by business_number (or normalized vendor name) → DerivedStatus."""
        groups: dict[str, list[ContractRecord]] = {}
        for r in records:
            key = r.business_number.strip() if r.business_number.strip() else _normalize_name(r.vendor_name)
            groups.setdefault(key, []).append(r)

        result: dict[str, DerivedStatus] = {}
        for key, group in groups.items():
            sources = list({r.source for r in group})
            business_name = group[0].vendor_name
            business_number = next((r.business_number for r in group if r.business_number), key)

            # Active if at least one non-cancelled, non-revoked contract record
            any_active = any(r.status not in ("cancelled", "revoked", "terminated") for r in group)
            status = "active" if any_active else "revoked"

            result[key] = DerivedStatus(
                business_number=business_number,
                business_name=business_name,
                status=status,
                data_sources=sources,
            )
        return result
