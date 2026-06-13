import cbor2
import base58

# P-256 (secp256r1) multicodec prefix: varint(0x1200) = [0x80, 0x24]
_P256_MULTICODEC = bytes([0x80, 0x24])

def derive_did_key_from_cose(cose_bytes: bytes) -> str:
    """Derive did:key from a COSE_Key-encoded P-256 public key.

    Algorithm:
    1. Decode COSE map to get x and y coordinates (32 bytes each)
    2. Form compressed point: 0x02|0x03 prefix + x (33 bytes)
    3. Prepend P-256 multicodec prefix [0x80, 0x24]
    4. Base58btc encode, prefix with 'z'
    """
    cose = cbor2.loads(cose_bytes)
    x: bytes = cose[-2]  # COSE -2 = x
    y: bytes = cose[-3]  # COSE -3 = y

    # SEC1 compressed point: 0x02 if y is even, 0x03 if odd
    prefix = 0x02 if y[-1] % 2 == 0 else 0x03
    compressed = bytes([prefix]) + x

    multicodec_key = _P256_MULTICODEC + compressed
    encoded = base58.b58encode(multicodec_key).decode()
    return f"did:key:z{encoded}"
