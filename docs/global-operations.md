# Global Operations Runbook

This project is still not a value-custody mainnet. The goal of this runbook is to move safely from lab PoC to globally reachable test networks.

## Network Stages

| Stage | Purpose | Promotion gate |
|---|---|---|
| Devnet | Local and CI validation | Unit tests, protocol vectors, deterministic genesis |
| Private testnet | 5-20 controlled nodes | Reorg tests, peer churn tests, archive/pruned node sync |
| Public testnet | Internet-facing, no value | Bootnodes, ban scoring, strict resource limits, monitoring |
| Incentivized testnet | Adversarial load | External audit started, bug bounty, incident process |
| Limited mainnet candidate | Low economic limit | Audit closure, signed release, SBOM, reproducible build evidence |

## Required Public Node Configuration

Use explicit network identity and bootnodes:

```bash
export PQC_CHAIN_ID="pqc-chain-public-testnet-2026-ml-dsa-87-v2"
export PUBLIC_HOST="node1.example.org"
export BOOTNODES="boot1.example.org:8000,boot2.example.org:8000"
export ARCHIVE_NODE=1
export PRUNE_DEPTH=0
export PQC_STRICT_TLS=1
export PQC_TLS_CA_FILE="/etc/pqc-chain/ca.pem"
python Quantum.py
```

Self-signed TLS without verification is acceptable for local devnet only. Public nodes must use a CA bundle or pinned operational PKI and must keep the signed P2P node identity stable.

Normal wallet users should not run this operator profile. They should use outbound-only mode:

```bash
python Quantum.py --network public-testnet --role user --connect-only
```

That mode connects to bootnodes and receives data over outbound sockets, so home users do not need router changes or a public IP.

## Consensus Operations

- Run at least two independent archive nodes before launching public peers.
- Keep pruned nodes behind archive nodes for deep reorg recovery.
- Export UTXO snapshots after planned checkpoints and record `snapshot_hash`.
- Do not prune block bodies on explorer, audit, bridge, exchange, or bootnode infrastructure.
- Treat any failed replay during reorg as an incident.

## Wallet Operations

- Do not run hot wallets on public bootnodes.
- Use the interactive wallet only for devnet and low-value testnet operations.
- For public testnet and later, sign offline and broadcast from a separate node.
- Require human review for seed import/export and keep seeds off shared hosts.

## Monitoring

Track at minimum:

- Height, tip hash, accumulated work.
- Orphan block count.
- Peer count, ban score events, malformed payload count.
- Mempool bytes and eviction count.
- Reorg events and replay failures.
- Snapshot creation and verification.

## Incident Response

Pause promotion immediately when any of these occur:

- Main-chain replay failure.
- Inconsistent UTXO snapshot between archive nodes.
- Repeated malformed compressed payloads from diverse peers.
- Divergent tips among controlled archive nodes after expected network propagation.
- Any wallet seed or node key exposure.
