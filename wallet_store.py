import os
import struct
from typing import Dict, List


BINARY_WALLET_FILE = "wallets.bin"
LEGACY_WALLET_FILE = "wallets.json"
WALLET_MAGIC = b"PQCWALLETSTORE"
WALLET_VERSION = 2
MAX_WALLETS = 1024
MAX_FIELD_SIZE = 2 * 1024 * 1024


def wallet_store_exists(storage) -> bool:
    return (
        os.path.exists(os.path.join(storage.storage_dir, BINARY_WALLET_FILE))
        or os.path.exists(os.path.join(storage.storage_dir, LEGACY_WALLET_FILE))
    )


def _pack_bytes(buf: bytearray, value: bytes):
    if len(value) > MAX_FIELD_SIZE:
        raise ValueError("Wallet field is too large.")
    buf.extend(struct.pack(">I", len(value)))
    buf.extend(value)


def _unpack_bytes(data: bytes, offset: int) -> tuple[bytes, int]:
    if offset + 4 > len(data):
        raise ValueError("Truncated wallet field length.")
    size = struct.unpack(">I", data[offset:offset + 4])[0]
    offset += 4
    if size > MAX_FIELD_SIZE or offset + size > len(data):
        raise ValueError("Invalid wallet field size.")
    return data[offset:offset + size], offset + size


def _split_public_key(public_key: str) -> tuple[bytes, bytes]:
    parts = public_key.split(":")
    if len(parts) != 2:
        raise ValueError("Invalid wallet public key framing.")
    return bytes.fromhex(parts[0]), bytes.fromhex(parts[1])


def _normalize_record(record: Dict[str, str]) -> Dict[str, bytes | str]:
    ml_pk, ed_pk = _split_public_key(record["public_key"])
    return {
        "address": record["address"],
        "ml_pk": ml_pk,
        "ed_pk": ed_pk,
        "stored_key": bytes.fromhex(record["private_key"]),
        "salt": bytes.fromhex(record["salt"]),
        "password_hash": bytes.fromhex(record["password_hash"]),
    }


def encode_wallet_data(wallet_data: Dict[str, List[Dict[str, str]]]) -> bytes:
    records = [_normalize_record(record) for record in wallet_data.get("wallets", [])]
    if len(records) > MAX_WALLETS:
        raise ValueError("Too many wallets in local store.")

    buf = bytearray()
    buf.extend(WALLET_MAGIC)
    buf.extend(struct.pack(">H", WALLET_VERSION))
    buf.extend(struct.pack(">I", len(records)))
    for record in records:
        _pack_bytes(buf, record["address"].encode("ascii"))
        _pack_bytes(buf, record["ml_pk"])
        _pack_bytes(buf, record["ed_pk"])
        _pack_bytes(buf, record["stored_key"])
        _pack_bytes(buf, record["salt"])
        _pack_bytes(buf, record["password_hash"])
    return bytes(buf)


def decode_wallet_data(data: bytes) -> Dict[str, List[Dict[str, str]]]:
    if not data:
        return {"wallets": []}
    offset = len(WALLET_MAGIC)
    if not data.startswith(WALLET_MAGIC):
        raise ValueError("Invalid wallet store magic.")
    if offset + 6 > len(data):
        raise ValueError("Truncated wallet store header.")

    version = struct.unpack(">H", data[offset:offset + 2])[0]
    offset += 2
    if version != WALLET_VERSION:
        raise ValueError(f"Unsupported wallet store version: {version}")

    count = struct.unpack(">I", data[offset:offset + 4])[0]
    offset += 4
    if count > MAX_WALLETS:
        raise ValueError("Wallet count exceeds safety limit.")

    wallets = []
    for _ in range(count):
        address_b, offset = _unpack_bytes(data, offset)
        ml_pk, offset = _unpack_bytes(data, offset)
        ed_pk, offset = _unpack_bytes(data, offset)
        stored_key, offset = _unpack_bytes(data, offset)
        salt, offset = _unpack_bytes(data, offset)
        password_hash, offset = _unpack_bytes(data, offset)
        wallets.append({
            "address": address_b.decode("ascii"),
            "public_key": f"{ml_pk.hex()}:{ed_pk.hex()}",
            "private_key": stored_key.hex(),
            "salt": salt.hex(),
            "password_hash": password_hash.hex(),
        })

    if offset != len(data):
        raise ValueError("Unexpected trailing data in wallet store.")
    return {"wallets": wallets}


def save_wallet_data(storage, wallet_data: Dict[str, List[Dict[str, str]]]):
    storage.save_bytes(BINARY_WALLET_FILE, encode_wallet_data(wallet_data))


def load_wallet_data(storage) -> Dict[str, List[Dict[str, str]]]:
    binary_data = storage.load_bytes(BINARY_WALLET_FILE)
    if binary_data:
        return decode_wallet_data(binary_data)

    legacy_data = storage.load_data(LEGACY_WALLET_FILE)
    if legacy_data.get("wallets"):
        save_wallet_data(storage, legacy_data)
    return legacy_data
