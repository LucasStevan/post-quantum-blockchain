# Encoding Migration Notes

This file records the serialization changes that are safe to apply now and the
changes that must be treated as a protocol migration.

## Applied Now

### Wallet store moved out of compressed JSON

The local wallet store no longer writes new wallet records as hex strings inside
compressed JSON. New writes use `wallets.bin`, a versioned binary envelope.

Implementation points:

- `wallet_store.py` owns the binary wallet encoding.
- `EncryptedStorage.save_bytes()` and `EncryptedStorage.load_bytes()` encrypt raw
  bytes with the existing ChaCha20-Poly1305 storage key without zstd compression.
- `Wallet.load()` and the interactive wallet creation/import flow use
  `load_wallet_data()` / `save_wallet_data()`.
- Existing `wallets.json` stores are still readable. On read, the code writes a
  compatible `wallets.bin` copy and keeps the old file in place for rollback
  safety.

Why this is safer:

- Secret-bearing wallet records are no longer compressed before storage.
- Private wallet material is no longer represented as large hex strings in JSON.
- The wallet serialization is versioned and length-prefixed.
- The change is local-only and does not alter transaction IDs, block hashes, P2P
  messages, or user addresses.

Residual compatibility note:

- Legacy `wallets.json` is intentionally not deleted automatically. Operators can
  remove it manually after confirming `wallets.bin` unlocks correctly.

## Deferred

### Protobuf for P2P, storage, or consensus

Protobuf is a good direction for P2P and non-consensus storage, but it is not a
safe drop-in replacement in this patch.

Reasons:

- Current nodes exchange JSON+zstd payloads. Replacing that directly would break
  network compatibility.
- Consensus data needs canonical encoding. Generic Protobuf serialization can
  differ around unknown fields, default values, map ordering, and implementation
  behavior.
- Transactions still use a manual `struct`-based hash. Any consensus encoding
  migration must be versioned and tested with fixed vectors.

Safe future plan:

1. Add new P2P message types for Protobuf payloads while still accepting the
   current JSON+zstd messages.
2. Introduce `.proto` files for tx/block transport objects.
3. Use deterministic serialization for transport only.
4. Keep consensus hashing on the current canonical `struct` encoder until a
   separate v3 transaction format is designed.
5. If consensus moves to Protobuf, define a canonical subset, reject unknown
   consensus fields, remove floats, and publish test vectors.

## Explicit Non-Goals In This Patch

- No P2P wire-format change.
- No block storage migration.
- No transaction ID format change beyond the already-applied v2 chain binding.
- No forced deletion of legacy wallet files.
