import pytest
import cbor2
from portal.did_key import derive_did_key_from_cose

# Minimal valid COSE_Key for P-256 (kty=2, crv=1, x=32bytes, y=32bytes)
COSE_KEY = cbor2.dumps({
    1: 2,           # kty: EC2
    3: -7,          # alg: ES256
    -1: 1,          # crv: P-256
    -2: b"\x01" * 32,  # x coordinate
    -3: b"\x02" * 32,  # y coordinate
})

def test_derive_did_key_starts_with_prefix():
    did = derive_did_key_from_cose(COSE_KEY)
    assert did.startswith("did:key:z")

def test_derive_did_key_is_deterministic():
    did1 = derive_did_key_from_cose(COSE_KEY)
    did2 = derive_did_key_from_cose(COSE_KEY)
    assert did1 == did2

def test_derive_did_key_different_keys_different_dids():
    cose2 = cbor2.dumps({1: 2, 3: -7, -1: 1, -2: b"\x03" * 32, -3: b"\x04" * 32})
    did1 = derive_did_key_from_cose(COSE_KEY)
    did2 = derive_did_key_from_cose(cose2)
    assert did1 != did2
