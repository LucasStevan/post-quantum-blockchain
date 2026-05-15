import unittest

from wallet_store import BINARY_WALLET_FILE, decode_wallet_data, encode_wallet_data, load_wallet_data


class FakeStorage:
    def __init__(self, legacy_data):
        self.storage_dir = "."
        self.legacy_data = legacy_data
        self.saved = {}

    def load_bytes(self, filename):
        return self.saved.get(filename, b"")

    def save_bytes(self, filename, data):
        self.saved[filename] = data

    def load_data(self, filename):
        return self.legacy_data


class WalletStoreTests(unittest.TestCase):
    def test_wallet_store_binary_roundtrip_preserves_legacy_shape(self):
        wallet_data = {
            "wallets": [{
                "address": "a" * 128,
                "public_key": f"{'01' * 2592}:{'02' * 32}",
                "private_key": ("03" * 32) + ("04" * 12) + ("05" * 48),
                "salt": "06" * 32,
                "password_hash": "07" * 96,
            }]
        }

        encoded = encode_wallet_data(wallet_data)
        decoded = decode_wallet_data(encoded)

        self.assertIsInstance(encoded, bytes)
        self.assertEqual(decoded, wallet_data)

    def test_legacy_wallet_json_is_migrated_without_data_loss(self):
        wallet_data = {
            "wallets": [{
                "address": "b" * 128,
                "public_key": f"{'11' * 2592}:{'22' * 32}",
                "private_key": ("33" * 32) + ("44" * 12) + ("55" * 48),
                "salt": "66" * 32,
                "password_hash": "77" * 96,
            }]
        }
        storage = FakeStorage(wallet_data)

        loaded = load_wallet_data(storage)

        self.assertEqual(loaded, wallet_data)
        self.assertIn(BINARY_WALLET_FILE, storage.saved)
        self.assertEqual(decode_wallet_data(storage.saved[BINARY_WALLET_FILE]), wallet_data)


if __name__ == "__main__":
    unittest.main()
