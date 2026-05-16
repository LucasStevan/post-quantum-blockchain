# Home Test And Bootnode Setup

## What The Domain Means

`seu-dominio.com:8000` is not a magic blockchain name. It is a DNS name that points to a machine running a public PQC-CHAIN bootnode.

Example:

- You own `example.org`.
- You create a DNS `A` record: `seed1.example.org -> 203.0.113.10`.
- You run the node on that machine at port `8000`.
- Users configure only `seed1.example.org:8000`; they never need to know the IP.

For a normal wallet user, no router configuration is needed. The app runs in outbound-only mode and connects to bootnodes. For a public bootnode, someone must provide a reachable endpoint: VPS, datacenter node, or a tunnel/relay that gives you a public hostname and port.

Do not invent a new `PQC_CHAIN_ID` for a published network unless you also regenerate and publish a matching genesis block and test vectors. The current profiles intentionally use the checked-in v2 genesis domain.

## Test 1: One Computer

Double-click:

```text
run_local_devnet.bat
```

The app creates or unlocks a wallet, starts the node, and keeps data in `blockchain_data_local`.

## Test 2: Two Computers On Your LAN

On computer A:

```powershell
python Quantum.py --network local-devnet --role bootnode --public-host 192.168.1.50 --no-wallet
```

Use the actual LAN IP of computer A.

On computer B:

```powershell
python Quantum.py --network local-devnet --role user --bootnode 192.168.1.50:8000 --connect-only
```

Computer B does not need router configuration because it makes an outbound connection to computer A.

## Test 3: Someone In Another Country

At least one bootnode must be reachable from the public internet.

Recommended production-like setup:

1. Rent a small VPS.
2. Point `seed1.yourdomain.com` to the VPS public IP.
3. Open TCP port `8000` on the VPS firewall.
4. Run:

```bash
python Quantum.py --network bootnode --role bootnode --public-host seed1.yourdomain.com --no-wallet
```

The remote user runs:

```bash
python Quantum.py --network public-testnet --role user --bootnode seed1.yourdomain.com:8000 --connect-only
```

After you publish `seed1.yourdomain.com:8000` in `networks/public-testnet.yaml`, normal users can just run:

```text
run_public_testnet.bat
```

## Why Users Do Not Need Port Forwarding

The node supports outbound-only mode:

- It does not advertise itself as a public peer.
- It connects to bootnodes.
- It receives blocks and peer lists over the outbound WebSocket it opened.

This is the right default for home wallets. Public routing is only required for bootnodes, archive nodes, explorers, miners, and infrastructure operators.

## Before Mainnet

Do not call this mainnet until:

- You operate at least 5 geographically separated archive bootnodes.
- DNS seeds point to several independent nodes.
- TLS/pinning policy is finalized.
- Reorg, sync, fuzz, and long-run tests pass in CI.
- Releases are signed and audited.
