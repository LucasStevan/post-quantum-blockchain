import json
import os
from pathlib import Path

from Quantum import GENESIS_BLOCK_JSON, GENESIS_HASH, PROTOCOL_VERSION, TX_HASH_DOMAIN, Block


ROOT = Path(__file__).resolve().parents[1]
VECTOR_PATH = ROOT / "test_vectors" / "protocol_v2.json"


def main():
    vector = json.loads(VECTOR_PATH.read_text())
    os.environ["PQC_CHAIN_ID"] = vector["chain_id"]

    genesis = Block.from_dict(json.loads(GENESIS_BLOCK_JSON))

    assert vector["protocol_version"] == PROTOCOL_VERSION
    assert vector["tx_hash_domain"].encode() == TX_HASH_DOMAIN
    assert vector["genesis_hash"] == GENESIS_HASH == genesis.hash
    assert vector["genesis_merkle_root"] == genesis.compute_merkle_root()
    assert vector["genesis_coinbase_tx_id"] == genesis.transactions[0].tx_id
    assert genesis.hash == genesis.compute_hash()
    assert genesis.transactions[0].has_valid_id()
    print("protocol v2 vectors verified")


if __name__ == "__main__":
    main()
