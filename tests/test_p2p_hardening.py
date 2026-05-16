import os
import tempfile
import unittest

from Quantum import BAN_SCORE_THRESHOLD, Blockchain, Configuration, EncryptedStorage, MAX_WIRE_MESSAGE_BYTES, safe_zstd_json_loads


class P2PHardeningTests(unittest.TestCase):
    def setUp(self):
        self._old_chain_id = os.environ.get("PQC_CHAIN_ID")
        os.environ["PQC_CHAIN_ID"] = "pqc-chain-mainnet-2026-ml-dsa-87-v2"
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()
        if self._old_chain_id is None:
            os.environ.pop("PQC_CHAIN_ID", None)
        else:
            os.environ["PQC_CHAIN_ID"] = self._old_chain_id

    def make_chain(self, port=19100):
        config = Configuration()
        config.storage_dir = self.tmp.name
        config.public_host = "127.0.0.1"
        config.port = port
        storage = EncryptedStorage("b" * 128, self.tmp.name)
        return Blockchain(storage, "127.0.0.1", port, config)

    def test_node_identity_is_persistent_and_handshake_is_domain_bound(self):
        chain = self.make_chain()
        node_id = chain.node_id
        handshake = chain.build_handshake()

        self.assertEqual(chain.verify_handshake(handshake)["peer"], chain.own_address)

        handshake["chain_id"] = "other-chain"
        self.assertIsNone(chain.verify_handshake(handshake))
        try:
            chain.db.close()
        except Exception:
            pass

        reopened = self.make_chain()
        self.assertEqual(reopened.node_id, node_id)
        try:
            reopened.db.close()
        except Exception:
            pass

    def test_peer_ban_score_threshold_is_enforced(self):
        chain = self.make_chain()
        chain.record_peer_violation("203.0.113.10", BAN_SCORE_THRESHOLD, "test")

        self.assertIn("203.0.113.10", chain.banned_peers)
        try:
            chain.db.close()
        except Exception:
            pass

    def test_oversized_compressed_payload_is_rejected_before_decompression(self):
        with self.assertRaises(ValueError):
            safe_zstd_json_loads(b"x" * (MAX_WIRE_MESSAGE_BYTES + 1))


if __name__ == "__main__":
    unittest.main()
