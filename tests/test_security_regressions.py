import json
import os
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from Quantum import GENESIS_BLOCK_JSON, GENESIS_HASH, Block, MLDSA87, Transaction, TxIn, TxOut, Wallet


class SecurityRegressionTests(unittest.TestCase):
    def setUp(self):
        self._old_chain_id = os.environ.get("PQC_CHAIN_ID")

    def tearDown(self):
        if self._old_chain_id is None:
            os.environ.pop("PQC_CHAIN_ID", None)
        else:
            os.environ["PQC_CHAIN_ID"] = self._old_chain_id

    def test_chain_id_changes_transaction_hash(self):
        os.environ["PQC_CHAIN_ID"] = "pqc-chain-a"
        tx_a = Transaction(
            inputs=[TxIn("b" * 128, 0)],
            outputs=[TxOut(100, "a" * 128)],
            timestamp=1.0,
        )

        os.environ["PQC_CHAIN_ID"] = "pqc-chain-b"
        tx_b = Transaction(
            inputs=[TxIn("b" * 128, 0)],
            outputs=[TxOut(100, "a" * 128)],
            timestamp=1.0,
        )

        self.assertNotEqual(tx_a.tx_id, tx_b.tx_id)

    def test_tampered_transaction_id_is_rejected(self):
        os.environ["PQC_CHAIN_ID"] = "pqc-chain-a"
        tx = Transaction(
            inputs=[TxIn("b" * 128, 0)],
            outputs=[TxOut(100, "a" * 128)],
            timestamp=1.0,
        )
        raw = tx.to_dict()
        raw["outputs"][0]["amount"] = 101

        tampered = Transaction.from_dict(raw)

        self.assertFalse(tampered.has_valid_id())

    def test_default_genesis_matches_v2_transaction_domain(self):
        os.environ["PQC_CHAIN_ID"] = "pqc-chain-mainnet-2026-ml-dsa-87-v2"

        genesis = Block.from_dict(json.loads(GENESIS_BLOCK_JSON))

        self.assertEqual(genesis.hash, GENESIS_HASH)
        self.assertEqual(genesis.merkle_root, genesis.compute_merkle_root())
        self.assertEqual(genesis.hash, genesis.compute_hash())
        self.assertTrue(genesis.transactions[0].has_valid_id())

    def test_mldsa_seed_keygen_is_stable_and_verifies(self):
        seed = bytes.fromhex("42" * 32)
        ml_pk_a, ml_sk_a = MLDSA87.keygen_from_seed(seed)
        ml_pk_b, ml_sk_b = MLDSA87.keygen_from_seed(seed)
        ed_sk = ed25519.Ed25519PrivateKey.from_private_bytes(seed)
        ed_pk = ed_sk.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        message = b"security-regression"
        wallet = Wallet(
            ml_pk=ml_pk_a,
            ed_pk=ed_pk,
            stored_key=b"",
            address="",
            salt=b"",
            password_hash=b"",
            ml_sk_raw=ml_sk_a,
            ed_sk_raw=ed_sk,
        )

        self.assertEqual(ml_pk_a, ml_pk_b)
        self.assertEqual(ml_sk_a, ml_sk_b)
        self.assertTrue(Wallet.verify_signature(ml_pk_a, ed_pk, message, wallet.sign(message)))


if __name__ == "__main__":
    unittest.main()
