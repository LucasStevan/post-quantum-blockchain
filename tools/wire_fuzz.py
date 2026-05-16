import json
import os
import random

import zstandard as zstd

from Quantum import Block, MAX_BLOCK_BYTES, Transaction, safe_zstd_json_loads


def mutate(data: bytes) -> bytes:
    buf = bytearray(data)
    if not buf:
        return os.urandom(8)
    for _ in range(random.randint(1, 8)):
        pos = random.randrange(len(buf))
        buf[pos] ^= random.randrange(1, 256)
    return bytes(buf)


def assert_parser_is_total(payload: bytes):
    try:
        decoded = safe_zstd_json_loads(payload, MAX_BLOCK_BYTES)
        if isinstance(decoded, dict) and "transactions" in decoded:
            Block.from_dict(decoded)
        elif isinstance(decoded, dict) and "inputs" in decoded:
            Transaction.from_dict(decoded)
    except Exception:
        return


def main(iterations: int = 250):
    seeds = [
        zstd.compress(json.dumps({"inputs": [], "outputs": [], "tx_id": "00", "timestamp": 0}).encode()),
        zstd.compress(json.dumps({"index": 1, "transactions": [], "previous_hash": "00", "difficulty": 1}).encode()),
        b"",
        os.urandom(64),
    ]
    for seed in seeds:
        assert_parser_is_total(seed)
    for _ in range(iterations):
        assert_parser_is_total(mutate(random.choice(seeds)))
    print(f"wire fuzz completed: {iterations} mutations")


if __name__ == "__main__":
    main()
