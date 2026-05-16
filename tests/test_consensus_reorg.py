import asyncio
import json
import os
import tempfile
import unittest

from Quantum import (
    Block,
    Blockchain,
    Configuration,
    EncryptedStorage,
    GENESIS_BLOCK_JSON,
    TARGET_BLOCK_TIME,
    Transaction,
    TxOut,
)


class ConsensusReorgTests(unittest.TestCase):
    def setUp(self):
        self._old_chain_id = os.environ.get("PQC_CHAIN_ID")
        os.environ["PQC_CHAIN_ID"] = "pqc-chain-mainnet-2026-ml-dsa-87-v2"
        self.tmp = tempfile.TemporaryDirectory()
        config = Configuration()
        config.storage_dir = self.tmp.name
        config.public_host = "127.0.0.1"
        config.port = 19000
        config.archive_node = True
        config.prune_depth = 0
        self.storage = EncryptedStorage("a" * 128, self.tmp.name)
        self.chain = Blockchain(self.storage, "127.0.0.1", 19000, config)
        self.genesis = json.loads(GENESIS_BLOCK_JSON)
        self.genesis_ts = self.genesis["timestamp"]

    def tearDown(self):
        try:
            self.chain.db.close()
        except Exception:
            pass
        self.tmp.cleanup()
        if self._old_chain_id is None:
            os.environ.pop("PQC_CHAIN_ID", None)
        else:
            os.environ["PQC_CHAIN_ID"] = self._old_chain_id

    def make_block(self, parent, index, timestamp, address):
        parent_hash = parent.hash
        difficulty = self.chain.get_expected_difficulty_after(parent)
        reward = self.chain.get_reward(index, parent_hash, difficulty)
        coinbase = Transaction([], [TxOut(reward, address)], is_coinbase=True, timestamp=timestamp)
        block = Block(index, [coinbase], parent_hash, difficulty, timestamp=timestamp)
        asyncio.run(block.mine())
        return block

    def test_longer_fork_rebuilds_main_utxo_state(self):
        genesis_block = self.chain.get_block_by_hash(self.chain.latest_hash)
        main1 = self.make_block(genesis_block, 1, self.genesis_ts + TARGET_BLOCK_TIME, "a" * 128)
        self.assertTrue(asyncio.run(self.chain.add_block(main1, broadcast=False)))
        main2 = self.make_block(main1, 2, self.genesis_ts + TARGET_BLOCK_TIME * 2, "b" * 128)
        self.assertTrue(asyncio.run(self.chain.add_block(main2, broadcast=False)))

        fork1 = self.make_block(genesis_block, 1, self.genesis_ts + TARGET_BLOCK_TIME + 1, "c" * 128)
        fork2 = self.make_block(fork1, 2, self.genesis_ts + TARGET_BLOCK_TIME * 2 + 1, "d" * 128)
        fork3 = self.make_block(fork2, 3, self.genesis_ts + TARGET_BLOCK_TIME * 3 + 1, "e" * 128)

        self.assertFalse(asyncio.run(self.chain.add_block(fork2, broadcast=False)))
        self.assertIn(fork2.hash, self.chain.orphan_blocks)
        self.assertTrue(asyncio.run(self.chain.add_block(fork1, broadcast=False)))
        self.assertEqual(self.chain.latest_hash, main2.hash)

        self.assertTrue(asyncio.run(self.chain.add_block(fork3, broadcast=False)))

        self.assertEqual(self.chain.height, 3)
        self.assertEqual(self.chain.latest_hash, fork3.hash)
        self.assertIsNone(self.chain.get_utxo(main2.transactions[0].tx_id, 0))
        self.assertEqual(self.chain.get_utxo(fork3.transactions[0].tx_id, 0).address, "e" * 128)


if __name__ == "__main__":
    unittest.main()
