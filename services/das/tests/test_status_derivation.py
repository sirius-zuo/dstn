import pytest
from datetime import date, timedelta
from das.connectors.base import ContractRecord
from das.engine.status_derivation import StatusDerivationEngine, DerivedStatus

def make_record(bn="123456789", name="Acme Corp", status="active", end_days_ahead=30):
    return ContractRecord(
        business_number=bn,
        vendor_name=name,
        contract_date=date.today() - timedelta(days=90),
        contract_end_date=date.today() + timedelta(days=end_days_ahead),
        total_value=100000.0,
        status=status,
        reference_number="REF-001",
        source="canadabuys",
    )

def test_active_supplier_derives_active():
    engine = StatusDerivationEngine()
    result = engine.derive([make_record()])
    assert len(result) == 1
    assert result["123456789"].status == "active"
    assert result["123456789"].business_name == "Acme Corp"

def test_cancelled_contract_derives_revoked():
    engine = StatusDerivationEngine()
    result = engine.derive([make_record(status="cancelled")])
    assert result["123456789"].status == "revoked"

def test_multi_source_active_wins_over_single_cancelled():
    engine = StatusDerivationEngine()
    records = [
        make_record(bn="111", name="Corp A", status="active"),
        make_record(bn="111", name="Corp A", status="cancelled"),
    ]
    result = engine.derive(records)
    # At least one active contract → supplier is active
    assert result["111"].status == "active"

def test_no_bn_falls_back_to_vendor_name_key():
    engine = StatusDerivationEngine()
    records = [make_record(bn="", name="No BN Corp")]
    result = engine.derive(records)
    # keyed by vendor name when BN absent
    assert "no_bn_corp" in result or any(v.business_name == "No BN Corp" for v in result.values())
