import time
import json
from Quantum import Block, Transaction, TxOut

INITIAL_DIFFICULTY = 4
timestamp = time.time()

# Hardcoded initial coinbase transaction with a massive reward to the initial wallet
tx = Transaction(
    inputs=[],
    outputs=[TxOut(5000000000, "634518687b996f091d9467f1017e3e59419a3a447e7f0cfcf6d9ddb9cd105b13f05e646d9c5ebdc009f07837a6a215f19990e2b561ac30f5a1fdc31932188370")],
    is_coinbase=True,
    timestamp=timestamp
)

# Empty previous hash
previous_hash = "0" * 128

genesis_block = Block(
    index=0,
    transactions=[tx],
    previous_hash=previous_hash,
    difficulty=INITIAL_DIFFICULTY,
    timestamp=timestamp
)

# We need to mine the genesis block to meet the difficulty
import asyncio

async def mine_genesis():
    target = (1 << 512) - 1 >> genesis_block.difficulty
    while int(genesis_block.hash, 16) > target:
        genesis_block.nonce += 1
        genesis_block.hash = genesis_block.compute_hash()
    print(f"GENESIS_HASH = '{genesis_block.hash}'")
    print(f"GENESIS_BLOCK_JSON = '{json.dumps(genesis_block.to_dict())}'")

asyncio.run(mine_genesis())
