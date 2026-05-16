# Runbook Completo: Testnet, Bootnodes, Wallets E Caminho Para Mainnet

Este documento descreve como rodar o sistema de ponta a ponta, desde teste local em casa até uma testnet pública com bootnodes e o caminho operacional mínimo antes de uma mainnet.

O foco é tornar o uso simples para pessoas comuns:

- usuário final não precisa configurar IP;
- usuário final não precisa abrir porta no roteador;
- usuário final não precisa digitar variáveis de ambiente;
- operador de bootnode usa domínio público e VPS;
- desenvolvedores têm comandos claros para validar, empacotar e publicar releases.

## Status Honesto Do Projeto

O projeto está em estágio de **testnet pública experimental**, não em mainnet pronta para custodiar valor real.

Já existem avanços importantes:

- Assinaturas híbridas `ML-DSA-87 + Ed25519`.
- `chain_id` no hash assinado da transação.
- Proteção contra replay entre redes.
- Wallet store binário versionado.
- Fork-choice por trabalho acumulado.
- Orphan pool.
- Reorg por replay de UTXO.
- P2P com identidade persistente de nó.
- Perfis de rede em YAML.
- Modo outbound-only para usuários comuns.
- Guia de bootnode, DNS e VPS.
- CI, vetores de protocolo e smoke fuzz de wire payload.

Ainda falta antes de valor real:

- auditoria externa;
- bootnodes independentes;
- política final de TLS/pinning;
- testes longos de sincronização;
- release assinado;
- SBOM;
- monitoramento;
- plano de incidentes;
- revisão econômica de dificuldade, recompensas e fees.

## Glossário Rápido

| Termo | Significado |
|---|---|
| Nó | Processo que valida blocos/transações e fala P2P. |
| Wallet | Carteira local que cria seed, endereço e assina transações. |
| Bootnode | Nó público estável usado como ponto inicial de conexão. |
| Archive node | Nó que mantém todos os corpos de blocos. |
| Pruned node | Nó que remove corpos antigos e pode rejeitar reorgs profundos. |
| DNS seed | Nome DNS que aponta para um ou mais bootnodes. |
| `chain_id` | Identificador da rede usado no hash assinado. |
| Genesis | Primeiro bloco da rede. |
| Outbound-only | Modo usuário comum: conecta para fora, não aceita conexões públicas. |
| Mainnet | Rede com valor real, governança e operação madura. |
| Testnet | Rede pública sem valor real para testes. |

## Arquitetura Recomendada

### Para Usuários Comuns

Usuários comuns devem rodar:

```text
run_public_testnet.bat
```

ou:

```bash
python Quantum.py --network public-testnet --role user --connect-only
```

Esse modo:

- cria ou abre wallet;
- conecta a bootnodes;
- sincroniza blocos por conexões de saída;
- não exige IP público;
- não exige port forwarding;
- não anuncia o usuário como peer público.

### Para Operadores De Bootnode

Operadores rodam:

```bash
python Quantum.py --network bootnode --role bootnode --public-host seed1.seudominio.com --no-wallet
```

Esse modo:

- aceita conexões públicas;
- anuncia um domínio;
- roda como archive node;
- não abre wallet interativa;
- serve como ponto inicial para usuários comuns.

### Para Desenvolvedores

Desenvolvedores podem rodar:

```text
run_local_devnet.bat
```

ou:

```bash
python Quantum.py --network local-devnet --role user
```

## Perfis De Rede

Os perfis ficam em:

```text
networks/
```

Arquivos principais:

```text
networks/local-devnet.yaml
networks/public-testnet.yaml
networks/bootnode.yaml
```

### `local-devnet.yaml`

Uso:

- testes locais;
- desenvolvimento;
- rede de laboratório.

Características:

- archive node ativado;
- sem bootnodes públicos;
- sem DNS seed;
- TLS estrito desligado;
- dados em `blockchain_data_local`.

### `public-testnet.yaml`

Uso:

- usuários comuns;
- testnet pública;
- sincronização sem configurar roteador.

Exemplo atual:

```yaml
bootnodes:
  - bloxchain.duckdns.org:8000
dns_seeds:
  - bloxchain.duckdns.org:8000
connect_only: true
archive_node: false
prune_depth: 1000
```

### `bootnode.yaml`

Uso:

- VPS pública;
- nó arquivo;
- ponto de entrada da rede.

Características:

- `connect_only: false`;
- `archive_node: true`;
- `prune_depth: 0`;
- wallet desligada com `--no-wallet`.

## Passo A Passo: Testar Em Casa Sem VPS

Este teste confirma que o app roda, cria wallet e minera/sincroniza localmente.

### 1. Abrir Dev Container Ou Ambiente Python

O ambiente recomendado é o Dev Container, porque ele compila liboqs corretamente.

No VS Code:

1. Abra a pasta do projeto.
2. Execute `Dev Containers: Rebuild Container`.
3. Aguarde o build.
4. Abra um terminal dentro do container.

### 2. Rodar Devnet Local

No Windows:

```text
run_local_devnet.bat
```

Ou no terminal:

```bash
python Quantum.py --network local-devnet --role user
```

### 3. Criar Wallet

Ao iniciar pela primeira vez:

1. Escolha criar wallet.
2. Digite senha forte.
3. Salve as 24 palavras offline.
4. Nunca publique a seed.

### 4. Minerar Bloco Local

No menu:

```text
2. Mine block
```

Depois veja:

```text
Height
Confirmed balance
Pending balance
```

## Passo A Passo: Criar Um Bootnode Público

Este é o caminho para outra pessoa, em outro país, sincronizar por `bloxchain.duckdns.org:8000`.

### 1. Ter Um DNS

Você já conseguiu:

```text
bloxchain.duckdns.org
```

Esse DNS atualmente resolve para:

```text
190.89.157.27
```

Confirme com:

```powershell
nslookup bloxchain.duckdns.org
```

### 2. Escolher Onde O Bootnode Vai Rodar

Opção recomendada:

- VPS pública.

Opção possível, mas menos recomendada:

- seu computador de casa com port forwarding.

Para testnet real, prefira VPS.

### 3. Usar VPS

Na VPS, você precisa:

- Ubuntu LTS;
- IP público;
- porta TCP `8000` aberta;
- projeto instalado;
- Dev Container ou dependências instaladas;
- bootnode rodando 24/7.

Comando:

```bash
python Quantum.py --network bootnode --role bootnode --public-host bloxchain.duckdns.org --no-wallet
```

### 4. Usar Computador De Casa

Se usar sua casa:

1. Confirme seu IP externo:

```powershell
curl.exe https://ifconfig.me/ip
```

2. Confirme DNS:

```powershell
nslookup bloxchain.duckdns.org
```

3. Veja o IP local do PC:

```powershell
ipconfig
```

Exemplo:

```text
10.1.1.129
```

4. No roteador, crie port forwarding:

```text
Porta externa: 8000
Protocolo: TCP
IP interno: 10.1.1.129
Porta interna: 8000
```

5. No Windows, libere firewall:

```powershell
New-NetFirewallRule -DisplayName "PQC Chain P2P 8000" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000
```

6. Teste com servidor simples:

```powershell
python -m http.server 8000 --bind 0.0.0.0
```

7. De outra rede, teste:

```powershell
Test-NetConnection bloxchain.duckdns.org -Port 8000
```

Se aparecer:

```text
TcpTestSucceeded : True
```

a porta está aberta.

8. Pare o servidor HTTP e rode o bootnode:

```powershell
python Quantum.py --network bootnode --role bootnode --public-host bloxchain.duckdns.org --no-wallet
```

### 5. Se A Porta Não Abrir

Possíveis causas:

- nó não está rodando;
- firewall bloqueando;
- roteador sem port forwarding;
- provedor usa CGNAT;
- teste feito de dentro da mesma rede sem NAT loopback.

Compare:

- IP do `curl ifconfig.me`;
- IP WAN mostrado no roteador.

Se forem diferentes, provavelmente é CGNAT. Nesse caso, use VPS.

## Passo A Passo: Usuário Comum Conectando

Quando `networks/public-testnet.yaml` contém:

```yaml
bootnodes:
  - bloxchain.duckdns.org:8000
dns_seeds:
  - bloxchain.duckdns.org:8000
```

o usuário final só precisa abrir:

```text
run_public_testnet.bat
```

ou:

```bash
python Quantum.py --network public-testnet --role user --connect-only
```

O usuário:

- cria wallet;
- guarda seed;
- sincroniza;
- envia transações;
- não abre porta;
- não configura roteador;
- não sabe IP.

## Sincronização

A sincronização atual tem:

- handshake com `protocol_version`;
- validação de `chain_id`;
- validação de `genesis_hash`;
- troca básica de peers;
- sync por headers;
- pedido de blocos;
- orphan pool;
- fork-choice por trabalho acumulado;
- reorg por replay de UTXO.

Para mainnet futura, ainda precisa:

- header-first sync mais completo;
- blocos em lotes;
- múltiplos peers concorrentes;
- proteção mais forte contra eclipse attack;
- checkpoints opcionais;
- ban score mais sofisticado;
- métricas de sync;
- teste de milhões de blocos.

## Wallet

Estado atual:

- cria seed;
- importa seed;
- senha com input oculto;
- wallet store local criptografado;
- assinatura híbrida.

Uso recomendado:

- usuários comuns podem usar wallet local em testnet;
- bootnodes não devem carregar wallet;
- mainnet deve separar daemon e wallet;
- mainnet deve ter cold signing/watch-only/hardware signer.

## Explorer

O explorer/API roda em:

```text
porta P2P + 100
```

Se P2P é `8000`, API/explorer fica em:

```text
8100
```

Para expor em VPS:

```bash
sudo ufw allow 8100/tcp
```

Para usuários comuns, não é obrigatório expor explorer.

## Mainnet: O Que Precisa Antes

### Infraestrutura

Antes de mainnet:

- pelo menos 5 bootnodes;
- pelo menos 3 provedores;
- pelo menos 3 regiões;
- archive nodes independentes;
- monitoramento;
- alertas;
- backups;
- plano de incidentes.

Exemplo:

```text
seed1.seudominio.com -> Brasil, provedor A
seed2.seudominio.com -> EUA, provedor B
seed3.seudominio.com -> Europa, provedor C
seed4.seudominio.com -> Ásia, provedor D
seed5.seudominio.com -> Canadá, provedor E
```

### Segurança De Release

Antes de mainnet:

- CI obrigatório;
- testes unitários;
- fuzzing;
- vetores de protocolo;
- SBOM;
- release assinada;
- binários assinados;
- imagem Docker assinada;
- changelog;
- tag Git imutável.

### Auditoria

Antes de mainnet:

- auditoria criptográfica do combiner `ML-DSA-87 + Ed25519`;
- auditoria de consenso;
- auditoria P2P;
- auditoria wallet;
- revisão de supply chain;
- bug bounty.

### Consenso Econômico

Antes de mainnet:

- revisar emissão;
- revisar dificuldade;
- revisar recompensa;
- revisar fee market;
- simular hashrate variável;
- simular timestamp manipulation;
- simular partição de rede;
- simular reorgs longos.

## Comandos De Validação

Dentro do Dev Container:

```bash
python -m py_compile Quantum.py wallet_store.py generate_genesis.py tools/verify_vectors.py tools/wire_fuzz.py tools/verify_requirements_pinned.py
python tools/verify_requirements_pinned.py
python -m unittest discover -s tests
python tools/verify_vectors.py
python tools/wire_fuzz.py
```

No host Windows, se liboqs não estiver instalado, a suíte completa pode falhar. O caminho recomendado é o Dev Container.

## Empacotar Para Usuário Comum

O objetivo é entregar um executável.

Arquivos relevantes:

```text
pqc_app.py
run_pqc_node.bat
run_public_testnet.bat
packaging/QuantumNode.spec
tools/build_windows_exe.ps1
```

Build Windows:

```powershell
tools\build_windows_exe.ps1
```

Saída esperada:

```text
dist\QuantumNode.exe
```

Antes de publicar:

- assinar o `.exe`;
- gerar hash SHA256;
- anexar SBOM;
- publicar release no GitHub;
- documentar versão do protocolo.

## Checklist Testnet Pública

- `bloxchain.duckdns.org` resolvendo.
- Porta `8000` aberta no bootnode.
- Bootnode rodando com `--no-wallet`.
- `networks/public-testnet.yaml` apontando para bootnode real.
- Usuário consegue abrir `run_public_testnet.bat`.
- Nó usuário aparece com peers.
- Blocos sincronizam.
- Transações entram na mempool.
- Blocos minerados são propagados.
- Reorgs pequenos funcionam.
- Logs não mostram payload inválido em loop.

## Checklist Mainnet Candidata

- 5+ bootnodes.
- 2+ archive nodes independentes fora do time principal.
- 30+ dias de testnet pública sem reset crítico.
- Auditoria externa iniciada ou concluída.
- Releases assinadas.
- Build reproduzível.
- SBOM publicado.
- Documentação de incidente.
- Monitoramento público.
- Política de upgrade.
- Política de seed/wallet.
- Política de disclosure.

## Arquivos Que Nunca Devem Ir Para GitHub

Não publique:

```text
blockchain_data*/
.venv/
__pycache__/
*.pyc
wallets.bin
wallets.json
config.yaml gerado
db_key
cert.pem
key.pem
rocks_db/
```

Esses arquivos podem conter chaves, carteiras, dados locais ou cache.

## Resumo Operacional

Para usuário comum:

```text
Abrir run_public_testnet.bat
Criar wallet
Guardar seed
Sincronizar
Usar
```

Para operador de bootnode:

```bash
python Quantum.py --network bootnode --role bootnode --public-host bloxchain.duckdns.org --no-wallet
```

Para desenvolvedor:

```bash
python Quantum.py --network local-devnet --role user
```

Para mainnet:

```text
Não lançar antes de auditoria, release assinada, bootnodes independentes e testes longos.
```
