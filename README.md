# Blockchain Post-Quantum Chain

PQC-CHAIN é uma prova de conceito de blockchain em Python com assinaturas híbridas pós-quânticas. O projeto usa `ML-DSA-87` via liboqs, combinado com `Ed25519`, e valida transações com regra AND: uma transação só é aceita quando as duas assinaturas verificam sobre o mesmo `tx_id`.

O ambiente recomendado é o Dev Container. Ele compila liboqs de forma reproduzível, instala as dependências Python e evita o uso de implementações educacionais como `dilithium-py`.

## Estado De Segurança

| Área | Implementação atual |
|---|---|
| Assinaturas | `ML-DSA-87` + `Ed25519` com combiner AND |
| ML-DSA | liboqs nativo + `liboqs-python` |
| Replay protection | `PQC_CHAIN_ID` entra no `tx_id` assinado |
| Hash de transação | Domínio `PQC-CHAIN:TX:v2` + `chain_id` + campos canônicos |
| Wallet store | `wallets.bin`, envelope binário versionado, criptografado e sem compressão |
| Wallet legado | `wallets.json` ainda é lido e migrado para `wallets.bin` |
| Armazenamento local | ChaCha20-Poly1305 com chave derivada por HKDF |
| Senhas locais | Argon2id |
| P2P | WebSocket sobre TLS 1.3 |
| Dev Container | `python:3.11-bookworm`, liboqs `0.14.0`, `liboqs-python==0.14.1` |

Relatórios técnicos:

- [readme-issue.md](readme-issue.md): correções das issues de segurança, modelo de ameaças e runbook.
- [encoding-migration.md](encoding-migration.md): mudança do wallet store e plano seguro para Protobuf.

## Modelo De Ligações Da Rede

Os diagramas abaixo usam Mermaid para renderizar caixas e ligações no GitHub, em vez de blocos ASCII difíceis de ler.

### Antes Das Correções

```mermaid
flowchart LR
    wallet["Wallet / Seed"]
    dilithium["dilithium-py<br/>Dilithium5 educacional"]
    mlSig["Assinatura ML<br/>sem garantia constant-time"]
    ed["Ed25519"]
    txid["tx_id sem chain_id"]
    hybrid["Assinatura hibrida<br/>AND verify"]
    transport["Transaction JSON + zstd"]
    p2p["P2P WebSocket / TLS"]
    netA["Rede A<br/>mainnet"]
    netB["Rede B<br/>fork / testnet"]
    replay["Replay cross-network<br/>assinatura reaproveitavel"]
    legacyWallet["wallets.json"]
    jsonKeys["hex strings<br/>JSON + zstd + AEAD"]

    wallet --> dilithium --> mlSig --> hybrid
    wallet --> ed --> hybrid
    txid --> hybrid --> transport --> p2p
    p2p --> netA
    p2p --> netB
    netA --> replay
    netB --> replay
    legacyWallet --> jsonKeys

    classDef risk fill:#4a1822,stroke:#ff6b7a,color:#ffffff,stroke-width:2px;
    classDef weak fill:#3b2f1e,stroke:#f6c85f,color:#ffffff,stroke-width:2px;
    classDef neutral fill:#1f2937,stroke:#64748b,color:#ffffff;
    class replay risk;
    class dilithium,mlSig,txid,jsonKeys weak;
    class wallet,ed,hybrid,transport,p2p,netA,netB,legacyWallet neutral;
```

### Depois Das Correções

```mermaid
flowchart LR
    wallet["Wallet / Seed"]
    facade["MLDSA87 facade"]
    oqs["liboqs<br/>ML-DSA-87"]
    ed["Ed25519"]
    domain["TX_HASH_DOMAIN<br/>PQC_CHAIN_ID<br/>campos canonicos"]
    txid["tx_id v2<br/>domain-separated"]
    hybrid["Assinatura hibrida<br/>AND verify"]
    checks["Validacao de tamanhos<br/>ML-DSA verify<br/>Ed25519 verify"]
    transport["JSON + zstd<br/>transporte legado compativel"]
    p2p["P2P WebSocket<br/>TLS 1.3"]
    handshake["Handshake assina<br/>chain_id"]
    netA["Rede A<br/>Chain ID A"]
    netB["Rede B<br/>Chain ID B"]
    accept["Aceita tx A"]
    reject["Rejeita replay<br/>de tx A"]
    binWallet["wallets.bin"]
    envelope["Envelope binario<br/>versionado + AEAD<br/>sem compressao"]
    legacy["wallets.json legado<br/>lido e migrado<br/>rollback seguro"]

    wallet --> facade --> oqs --> hybrid
    wallet --> ed --> hybrid
    domain --> txid --> hybrid --> checks --> transport --> p2p --> handshake
    handshake --> netA --> accept
    handshake --> netB --> reject
    wallet --> binWallet --> envelope
    legacy -. migracao compativel .-> binWallet

    classDef secure fill:#123524,stroke:#22c55e,color:#ffffff,stroke-width:2px;
    classDef protocol fill:#1e3a5f,stroke:#60a5fa,color:#ffffff,stroke-width:2px;
    classDef reject fill:#3f1d1d,stroke:#f87171,color:#ffffff,stroke-width:2px;
    classDef store fill:#2b2440,stroke:#a78bfa,color:#ffffff,stroke-width:2px;
    class wallet,facade,oqs,ed,domain,txid,hybrid,checks,accept secure;
    class transport,p2p,handshake,netA,netB protocol;
    class reject reject;
    class binWallet,envelope,legacy store;
```

## Por Que Não Protobuf Agora?

Protobuf é uma boa direção para P2P e storage, mas não foi aplicado diretamente no consenso porque isso seria uma migração de protocolo. O formato atual de rede ainda é JSON+zstd para compatibilidade entre nós. O hash de transação usa encoder manual com `struct`, e qualquer migração de consenso precisa de canonicalização, versionamento e vetores de teste.

O que foi aplicado agora é local e compatível: carteiras novas usam `wallets.bin`; carteiras antigas em `wallets.json` continuam legíveis.

## Rodar Com Dev Container

Pré-requisitos:

- Docker Desktop
- VS Code
- Extensão Dev Containers

Passos:

1. Abra a raiz deste repositório no VS Code.
2. Execute `Dev Containers: Rebuild Container Without Cache` na primeira vez após as mudanças de imagem.
3. Aguarde o build. O Dockerfile compila liboqs e instala as dependências.
4. No terminal do container, rode:

```bash
python Quantum.py
```

O primeiro start cria `blockchain_data_<PORT>/config.yaml`, certificados TLS locais, banco RocksDB local e wallet store quando a carteira for criada/importada.

Se o log de build ainda mostrar `mcr.microsoft.com/devcontainers/python:1-3.11-bullseye`, o VS Code está usando configuração antiga ou log antigo. O log correto deve citar `docker.io/library/python:3.11-bookworm`.

## Rodar Um Nó Local

```bash
export PQC_CHAIN_ID="pqc-chain-mainnet-2026-ml-dsa-87-v2"
export PORT=8000
python Quantum.py
```

No PowerShell:

```powershell
$env:PQC_CHAIN_ID="pqc-chain-mainnet-2026-ml-dsa-87-v2"
$env:PORT="8000"
python Quantum.py
```

## Rodar Múltiplos Nós Locais

Use o mesmo `PQC_CHAIN_ID` para nós da mesma rede.

Nó inicial:

```bash
export PQC_CHAIN_ID="pqc-chain-mainnet-2026-ml-dsa-87-v2"
export PORT=8000
python Quantum.py
```

Segundo nó:

```bash
export PQC_CHAIN_ID="pqc-chain-mainnet-2026-ml-dsa-87-v2"
export INITIAL_NODE="127.0.0.1:8000"
export PORT=8001
python Quantum.py
```

Terceiro nó:

```bash
export PQC_CHAIN_ID="pqc-chain-mainnet-2026-ml-dsa-87-v2"
export INITIAL_NODE="127.0.0.1:8000"
export PORT=8002
python Quantum.py
```

Cada nó deve usar `STORAGE_DIR` próprio ou rodar em diretórios separados. Dois nós não devem compartilhar o mesmo `blockchain_data_<PORT>`.

## Testes E Verificações

Dentro do Dev Container:

```bash
python -m py_compile Quantum.py wallet_store.py generate_genesis.py
python -m unittest discover -s tests
python -c "import oqs; assert 'ML-DSA-87' in oqs.get_enabled_sig_mechanisms(); print(oqs.oqs_version())"
```

## Arquivos Locais Que Não Devem Ser Commitados

O `.gitignore` bloqueia dados gerados e sensíveis:

- `blockchain_data*/`
- `__pycache__/`
- caches de teste/ferramentas
- ambientes virtuais

`blockchain_data*/` pode conter `wallets.bin`, `wallets.json`, `config.yaml`, `db_key`, certificados e RocksDB. Não publique esses arquivos.

## Replay Protection

Transações v2 incluem `PQC_CHAIN_ID` no `tx_id`. Use identificadores diferentes para redes diferentes:

```bash
export PQC_CHAIN_ID="pqc-chain-mainnet-2026-ml-dsa-87-v2"
export PQC_CHAIN_ID="pqc-chain-testnet-2026-ml-dsa-87-v2"
export PQC_CHAIN_ID="pqc-chain-lab-fork-2026-05-15"
```

Se duas redes usam o mesmo `PQC_CHAIN_ID`, elas estão intencionalmente no mesmo domínio de assinatura.

## Limites Da PoC

Esta é uma PoC técnica, não uma mainnet pronta para custodiar valor real. O projeto não promete proteção contra host comprometido, malware local, engenharia social, supply chain maliciosa ou side-channel absoluto em hardware compartilhado. O modelo de ameaças completo está em [readme-issue.md](readme-issue.md).

## Estrutura Principal

| Caminho | Função |
|---|---|
| `Quantum.py` | Nó, wallet, transações, blocos, P2P e explorer API |
| `wallet_store.py` | Envelope binário versionado para carteiras locais |
| `.devcontainer/` | Build reproduzível com liboqs |
| `tests/` | Regressões de segurança e wallet store |
| `explorer/` | Interface web simples do explorer |
| `readme-issue.md` | Relatório técnico das issues corrigidas |
| `encoding-migration.md` | Decisões sobre wallet encoding e Protobuf |
