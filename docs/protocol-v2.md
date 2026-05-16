# PQC-CHAIN Protocol v2

This document is the normative engineering spec for the current protocol. Code and tests must match this file before a network is promoted between stages.

## Network Domain

- `protocol_version`: `2`
- `chain_id`: configured by `PQC_CHAIN_ID` and persisted in `config.yaml`
- `genesis_hash`: `04d0a6dcd5ec2218b8180b9a456158f79abaa4fe731772e8dd3c2ae7fdba4f5ae71a7947f62d6471ab7cf67d76e3c81c5148df231b662424eae3a99d7c433fcb`
- Transaction hash domain: `PQC-CHAIN:TX:v2`

Nodes must reject peer handshakes for a different `protocol_version`, `chain_id`, or `genesis_hash`.

## Transaction Validity

A transaction id is `SHA3-512` over canonical binary fields:

1. Domain length and domain bytes.
2. Chain id length and chain id bytes.
3. Coinbase flag.
4. Timestamp encoded as big-endian float64.
5. Each input transaction id and output index.
6. Each output amount and address.

Non-coinbase transactions are valid only when:

- `tx_id` equals the recomputed id.
- Every output has a positive integer amount no larger than `MAX_SUPPLY`.
- Every output address is 128 lowercase hex characters.
- Inputs do not double-spend within the transaction or block.
- Input public keys hash to the spent UTXO address.
- The hybrid signature verifies with:

```text
ML-DSA-87.Verify(pk_ml, tx_id, sig_ml)
AND Ed25519.Verify(pk_ed, tx_id, sig_ed)
```

## Block Validity

A block is valid only when:

- The parent exists, except for genesis.
- `index == parent.index + 1`.
- `difficulty == expected_difficulty(parent)`.
- `merkle_root` and `hash` recompute exactly.
- Proof-of-work satisfies the target implied by `difficulty`.
- Timestamp is greater than median-time-past of the previous 11 blocks.
- Timestamp is not more than two hours in the future according to local node time.
- The first transaction is coinbase and no later transaction is coinbase.
- Serialized block size is at most `MAX_BLOCK_BYTES`.
- Coinbase output sum is not greater than block subsidy plus transaction fees.

## Fork Choice And Reorg

The fork-choice rule is highest accumulated work. Work is currently represented as `2^difficulty` per block.

When a side chain becomes heavier than the current main chain, the node rebuilds main-chain state by replaying full block bodies from genesis to the new tip. Pruned nodes can reject deep reorgs if required block bodies are unavailable. Archive nodes must keep all block bodies.

## P2P Envelope

Message type byte:

- `0x01`: compressed transaction JSON.
- `0x02`: compressed block JSON.
- `0x03`: signed node handshake JSON.
- `0x04`: sync request containing peer height.
- `0x05`: peer list JSON.
- `0x06`: header sync request containing peer height and tip.
- `0x07`: compressed header list JSON.

Compressed wire messages must be rejected before decompression when larger than `MAX_WIRE_MESSAGE_BYTES`.

Normal wallet users may run `connect_only=true`. They open outbound WebSocket connections to bootnodes, listen on those outbound sockets, and do not advertise themselves as publicly reachable peers.

## Upgrade Rule

Consensus-breaking changes require:

- New `protocol_version`.
- New hash domain if transaction semantics change.
- New immutable test vectors.
- A migration document and staged network rollout.
