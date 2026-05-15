# Security Issue Runbook

Este documento registra a correção das issues 1, 2 e 3 e serve como runbook para rodar o projeto com o Dev Container em modo pós-quântico sério, sem depender de `dilithium-py`.

## Status das issues

| Issue | Risco | Correção aplicada |
|---|---|---|
| 1 | `dilithium-py` é educacional, Python puro e não constant-time | Removido de `requirements.txt`; assinaturas ML agora usam `ML-DSA-87` via `liboqs-python` + liboqs nativo no Dev Container. |
| 2 | Replay cross-chain porque `tx_id` não incluía rede/chain | `Transaction.compute_hash()` agora inclui domínio `PQC-CHAIN:TX:v2` e `PQC_CHAIN_ID`; validadores rejeitam `tx_id` que não bate com o conteúdo recomputado. |
| 3 | README não declarava ameaça, combiner e limites | Este arquivo documenta o modelo de ameaças, a claim do combiner híbrido e os limites operacionais. |

## O que mudou no código

- `Quantum.py` usa `MLDSA87`, uma camada pequena sobre `oqs.Signature("ML-DSA-87")`.
- O combiner continua sendo `ML-DSA-87 || Ed25519` com verificação AND.
- A seed phrase ainda recupera a carteira: o keygen ML-DSA usa RNG determinístico temporário, protegido por lock, apenas durante a geração da chave.
- A assinatura híbrida agora valida tamanhos exatos: prefixo de 4 bytes, assinatura ML-DSA e assinatura Ed25519 de 64 bytes.
- `PQC_CHAIN_ID` é persistido em `config.yaml` e entra no hash assinado da transação.
- O genesis hardcoded foi recalculado para a rede v2 padrão, de modo que `merkle_root` e `GENESIS_HASH` acompanham o domínio `PQC-CHAIN:TX:v2`.
- O handshake P2P inclui e assina `chain_id`, reduzindo mistura acidental entre mainnet/testnet/forks.
- Blocos novos validam `merkle_root`, `hash`, coinbase único, fees, recompensa máxima e double-spend dentro do bloco.
- `.gitignore` bloqueia `blockchain_data*/`, `__pycache__/` e caches locais para reduzir risco de commit acidental de carteiras, `db_key`, certificados e banco local.
- `wallet_store.py` move novos registros de carteira para `wallets.bin`, um envelope binário versionado, criptografado e sem compressão. O formato legado `wallets.json` continua legível e é migrado de forma compatível.
- `encoding-migration.md` documenta por que Protobuf foi adiado para uma migração de protocolo versionada, em vez de ser trocado de forma direta no consenso/P2P.

## Rodar 100% no Dev Container

Pré-requisitos na máquina host:

- Docker Desktop
- VS Code
- Extensão Dev Containers

Passos:

1. Abra a raiz do repositório no VS Code.
2. Escolha `Reopen in Container`.
3. Aguarde o build. O Dockerfile compila liboqs `0.14.0`, instala as dependências de `requirements.txt` dentro da imagem e verifica se `ML-DSA-87` está habilitado.
4. No terminal do container, rode:

```bash
python Quantum.py
```

O primeiro start cria `blockchain_data_<PORT>/config.yaml`, incluindo `db_key` e `chain_id`.

### Troubleshooting do rebuild

Se o rebuild falhar em `apt-get update` com `NO_PUBKEY 62D54FD4003F6525` para `https://dl.yarnpkg.com/debian`, a causa é um source Yarn herdado da imagem base antiga do Dev Container. O Dockerfile atual usa `python:3.11-bookworm` para evitar esse repositório externo quebrado.

O VS Code pode chamar o Dev Containers CLI com `--skip-post-create` em alguns fluxos de reopen/rebuild. Por isso, liboqs e os pacotes Python são instalados no Dockerfile, não apenas no `postCreateCommand`. Depois de atualizar o repositório, rode `Dev Containers: Rebuild Container` ou, se houver cache preso, `Dev Containers: Rebuild Container Without Cache`.

No log de build novo, a etapa de metadata deve citar `docker.io/library/python:3.11-bookworm`. Se ainda aparecer `mcr.microsoft.com/devcontainers/python:1-3.11-bullseye`, o VS Code está lendo uma configuração antiga ou um log antigo.

## Rodar múltiplos nós locais

Use o mesmo `PQC_CHAIN_ID` para nós da mesma rede.

Terminal 1:

```bash
export PQC_CHAIN_ID="pqc-chain-mainnet-2026-ml-dsa-87-v2"
export PORT=8000
python Quantum.py
```

Terminal 2:

```bash
export PQC_CHAIN_ID="pqc-chain-mainnet-2026-ml-dsa-87-v2"
export INITIAL_NODE="127.0.0.1:8000"
export PORT=8001
python Quantum.py
```

Terminal 3:

```bash
export PQC_CHAIN_ID="pqc-chain-mainnet-2026-ml-dsa-87-v2"
export INITIAL_NODE="127.0.0.1:8000"
export PORT=8002
python Quantum.py
```

No PowerShell, use:

```powershell
$env:PQC_CHAIN_ID="pqc-chain-mainnet-2026-ml-dsa-87-v2"
$env:INITIAL_NODE="127.0.0.1:8000"
$env:PORT="8001"
python Quantum.py
```

## Forks, testnets e replay protection

Nunca reutilize `PQC_CHAIN_ID` entre redes que devem ser isoladas.

Exemplos:

```bash
export PQC_CHAIN_ID="pqc-chain-mainnet-2026-ml-dsa-87-v2"
export PQC_CHAIN_ID="pqc-chain-testnet-2026-ml-dsa-87-v2"
export PQC_CHAIN_ID="pqc-chain-lab-fork-2026-05-15"
```

Uma transação assinada em uma rede não deve validar em outra, porque o `tx_id` assinado muda com o `chain_id`. Depois desta migração, dados antigos gerados com o hash v1 devem ser tratados como legado de laboratório; para uma rede limpa, mova `blockchain_data_*` para backup e inicialize novamente.

## Verificações rápidas

Dentro do Dev Container:

```bash
python -m py_compile Quantum.py generate_genesis.py
python -c "import oqs; assert 'ML-DSA-87' in oqs.get_enabled_sig_mechanisms(); print(oqs.oqs_version())"
python -m unittest discover -s tests
```

## Modelo de ameaças

| Classe de adversário | Em escopo? | Garantia |
|---|---:|---|
| Observador passivo de rede | Sim | P2P usa TLS 1.3; transações não dependem de segredo em trânsito para autenticidade. |
| MITM / rede ativa | Parcial | Handshake assinado e `chain_id` reduzem mistura de redes; certificados ainda são autoassinados nesta PoC. |
| Nó comprometido | Parcial | UTXO e cadeia de Merkle roots autenticam estado aceito; nó comprometido ainda pode censurar ou mentir localmente. |
| Replay entre forks/testnets | Sim | `PQC_CHAIN_ID` entra no `tx_id` assinado. |
| Observador de timing local | Mitigado no ML-DSA | Removido `dilithium-py`; liboqs substitui a implementação educacional. Side-channel de host/VM ainda depende do ambiente. |
| Criptanalista quântico CRQC | Sim para assinaturas clássicas, mitigado pelo híbrido | Shor quebra Ed25519, mas a transação ainda exige ML-DSA válido. |
| Quebra acadêmica de ML-DSA | Mitigado | Ed25519 continua exigido para gastar UTXO enquanto não houver CRQC prático. |
| Quebra de Ed25519 | Mitigado | ML-DSA continua exigido. |
| Quebra simultânea de ML-DSA e Ed25519 | Não | Risco catastrófico aceito. |
| Host do operador comprometido | Não | Malware pode roubar senha, seed, processo ou memória. |
| Supply chain maliciosa | Parcial | Dev Container fixa liboqs/liboqs-python; ainda é necessário auditar hashes/releases em produção. |

## Claim do combiner híbrido

A regra de validade é:

```text
Valid(tx) = ML-DSA.Verify(pk_ml, tx_id, sig_ml)
            AND Ed25519.Verify(pk_ed, tx_id, sig_ed)
```

As duas assinaturas cobrem o mesmo `tx_id`, e o encoding é prefixado por tamanho. A propriedade esperada é a segurança do combiner enquanto pelo menos um dos esquemas subjacentes continuar não forjável no modelo considerado. Esta é uma PoC de engenharia e ensino; para produção, exigir revisão criptográfica externa, vetores formais e hardening de side-channel por plataforma.

## Pruning

`PRUNE_DEPTH = 100` remove corpos de blocos antigos. Um nó pruned não reexecuta todo o histórico depois da poda; ele confia na cadeia de headers/Merkle roots já aceita. Operadores de exploradores, auditoria ou testemunhas devem rodar modo arquivo. Esse modo ainda não está implementado como flag; por enquanto, aumente `PRUNE_DEPTH` ou desative a poda no código antes de iniciar uma rede de auditoria.

## Fora de escopo

- Proteger seed phrase digitada em máquina comprometida.
- Proteger contra engenharia social.
- Garantir anonimato de rede.
- Garantir consenso econômico completo de mainnet real.
- Garantir side-channel resistance absoluta em hardware compartilhado, VM hostil ou Python runtime comprometido.

## Referências primárias

- NIST FIPS 204, Module-Lattice-Based Digital Signature Standard: https://csrc.nist.gov/pubs/fips/204/final
- Open Quantum Safe liboqs-python: https://github.com/open-quantum-safe/liboqs-python
- Open Quantum Safe liboqs: https://github.com/open-quantum-safe/liboqs
- EIP-155, Simple replay attack protection: https://eips-wg.github.io/EIPs/155/
- Bindel, Herath, McKague, Stebila, Transitioning to a Quantum-Resistant Public Key Infrastructure, PQCrypto 2017: https://www.douglas.stebila.ca/research/papers/PQCrypto-BHMS17/
