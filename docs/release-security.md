# Release Security And Audit Gates

This is the checklist for promoting a build beyond local and private test networks.

## Supply Chain

- Build inside `.devcontainer/Dockerfile`.
- Keep direct runtime dependencies exact-pinned in `requirements.txt`.
- Generate hash-locked Python requirements before a value-bearing release.
- Produce an SBOM for each release candidate.
- Sign release artifacts and container images.
- Record source commit, Docker image digest, SBOM digest, and test-vector version.
- Keep liboqs and liboqs-python versions aligned with the release notes.

References:

- SLSA: https://slsa.dev/
- OWASP Software Component Verification Standard: https://owasp.org/www-project-software-component-verification-standard/
- CISA Secure by Design: https://www.cisa.gov/securebydesign

## Required Tests

- `python -m py_compile Quantum.py wallet_store.py generate_genesis.py`
- `python -m unittest discover -s tests`
- Protocol vector verification.
- Reorg and partition simulations.
- Fuzzing for compressed P2P payloads, transaction decoding, and block decoding.
- Long-running archive/pruned node sync test.

## Required External Review

- Cryptographic review of the `ML-DSA-87 || Ed25519` AND combiner.
- Consensus review of fork-choice, reward schedule, difficulty adjustment, and reorg replay.
- P2P review of peer discovery, rate limits, ban scoring, and TLS/identity policy.
- Wallet review of seed handling, password KDF parameters, cold signing, and operational procedures.

For ML-DSA, the implementation target is NIST FIPS 204:

- https://csrc.nist.gov/pubs/fips/204/final

## No-Go Criteria

Do not promote to a value-bearing network if any item below is unresolved:

- Reorg can change tip without replaying UTXO state.
- Public nodes run with unauthenticated TLS by default.
- Wallet passwords or seeds are visible in terminal input.
- Protocol changes are not represented in immutable vectors.
- Release artifacts are unsigned or have no SBOM.
- Auditors have not reviewed the combiner and consensus rules.
