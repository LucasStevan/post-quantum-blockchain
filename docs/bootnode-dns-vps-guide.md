# Guia Didático: Domínio, DNS, VPS E Bootnode

Este guia explica como criar um endereço tipo `seed1.seudominio.com:8000` para que outras pessoas sincronizem o nó sem precisar saber IP, abrir roteador ou mexer em código.

## A Ideia Em Uma Frase

Um domínio como `seed1.seudominio.com` é só um apelido público para o IP de uma VPS onde você roda um bootnode.

```text
Usuário comum -> seed1.seudominio.com:8000 -> IP público da sua VPS -> PQC bootnode
```

Usuários comuns rodam em modo outbound-only. Eles não precisam abrir porta no roteador.

## O Que Você Precisa

- Uma VPS com IP público.
- Um domínio ou DNS dinâmico.
- Porta TCP `8000` liberada na VPS.
- O bootnode rodando com `--public-host`.

## Opção Mais Simples Para Teste

Use DNS dinâmico grátis:

- DuckDNS: `minhachain.duckdns.org`
- No-IP: `minhachain.ddns.net`

Com isso, seu bootnode pode ser:

```text
minhachain.duckdns.org:8000
```

Você não precisa comprar domínio para testar.

## Opção Recomendada Para Testnet Pública

Compre um domínio e use DNS gerenciado:

- Cloudflare DNS
- Registro.br, se quiser `.br`
- Porkbun, Namecheap ou outro registrador

Exemplo:

```text
seudominio.com
seed1.seudominio.com
seed2.seudominio.com
seed3.seudominio.com
```

## Criando A VPS

Você pode usar:

- Oracle Cloud Free Tier para testes grátis.
- Hetzner, DigitalOcean, Akamai/Linode, Vultr ou similares para VPS barata.

Para testnet inicial, uma VPS pequena já basta:

```text
1-2 vCPU
1-2 GB RAM
20-50 GB SSD
Ubuntu LTS
IP público IPv4
```

Para mainnet candidata, use máquinas melhores, monitoramento, backups, disco maior e provedores diferentes.

## Encontrando O IP Público Da VPS

No painel do provedor, procure por:

```text
Public IPv4
Public IP
External IP
```

Na própria VPS, você também pode rodar:

```bash
curl -4 ifconfig.me
```

Exemplo de resposta:

```text
203.0.113.10
```

Esse é o IP que entra no DNS.

## Configurando O DNS

No painel DNS do seu domínio, crie um registro:

```text
Tipo: A
Nome: seed1
Valor: 203.0.113.10
TTL: Auto
Proxy: DNS only
```

O resultado será:

```text
seed1.seudominio.com -> 203.0.113.10
```

Se usar Cloudflare, deixe como **DNS only**, nuvem cinza. Não use proxy laranja para a porta `8000`.

## Testando Se O DNS Funciona

No seu computador:

```bash
nslookup seed1.seudominio.com
```

Ou:

```bash
ping seed1.seudominio.com
```

O DNS deve resolver para o IP público da VPS.

## Liberando A Porta 8000 Na VPS

No firewall do provedor, libere entrada TCP:

```text
Porta: 8000
Protocolo: TCP
Origem: 0.0.0.0/0
```

No Ubuntu com `ufw`:

```bash
sudo ufw allow 8000/tcp
sudo ufw status
```

A API do explorer usa `porta + 100`, então para porta `8000` ela usa `8100`. Para expor o explorer, libere também:

```bash
sudo ufw allow 8100/tcp
```

## Rodando O Bootnode

Na VPS, dentro do projeto:

```bash
python Quantum.py --network bootnode --role bootnode --public-host seed1.seudominio.com --no-wallet
```

O bootnode:

- aceita conexões de outros nós;
- anuncia `seed1.seudominio.com:8000`;
- roda como archive node;
- não abre wallet interativa.

## Configurando A Rede Para Usuários Comuns

Edite:

```text
networks/public-testnet.yaml
```

Troque os exemplos:

```yaml
bootnodes:
  - seed1.pqc-chain.example:8000
  - seed2.pqc-chain.example:8000
dns_seeds:
  - dnsseed.pqc-chain.example:8000
```

Por seus bootnodes reais:

```yaml
bootnodes:
  - seed1.seudominio.com:8000
  - seed2.seudominio.com:8000
dns_seeds: []
```

Agora o usuário comum só precisa abrir:

```text
run_public_testnet.bat
```

Ou rodar:

```bash
python Quantum.py --network public-testnet --role user --connect-only
```

## O Que É Modo Outbound-Only?

Modo outbound-only significa:

- o usuário conecta em bootnodes;
- o usuário recebe blocos pela conexão que ele mesmo abriu;
- o usuário não anuncia IP público;
- o usuário não precisa abrir porta no roteador;
- funciona melhor para pessoas atrás de NAT, CGNAT, Wi-Fi doméstico ou redes corporativas.

Esse deve ser o padrão para wallet de usuário final.

## Posso Usar Meu Computador De Casa Como Bootnode?

Pode, mas não é recomendado.

Problemas comuns:

- IP residencial muda.
- Muitos provedores usam CGNAT.
- Precisa abrir porta no roteador.
- Quedas de energia derrubam a rede.
- Você expõe sua rede doméstica.

Para bootnode público, prefira VPS.

## Como Escalar Bootnodes

Comece com pelo menos três:

```text
seed1.seudominio.com -> VPS Brasil
seed2.seudominio.com -> VPS EUA
seed3.seudominio.com -> VPS Europa
```

Para mainnet candidata:

```text
5+ bootnodes
3+ provedores diferentes
3+ regiões geográficas
archive nodes independentes
monitoramento e alertas
backup de configs e chaves de nó
```

## Checklist Rápido

- VPS criada.
- IP público anotado.
- DNS `seed1.seudominio.com` apontando para o IP.
- Porta TCP `8000` liberada.
- Bootnode rodando com `--public-host seed1.seudominio.com`.
- `networks/public-testnet.yaml` atualizado.
- Usuário consegue rodar `run_public_testnet.bat`.

## Comandos De Diagnóstico

Ver se DNS resolve:

```bash
nslookup seed1.seudominio.com
```

Ver se a porta está aberta a partir de outra máquina:

```bash
nc -vz seed1.seudominio.com 8000
```

No PowerShell:

```powershell
Test-NetConnection seed1.seudominio.com -Port 8000
```

Ver logs do nó:

```bash
python Quantum.py --network bootnode --role bootnode --public-host seed1.seudominio.com --no-wallet
```

## Aviso De Produção

Este fluxo é adequado para devnet e public testnet. Antes de mainnet com valor real, ainda são necessários:

- TLS/pinning ou PKI operacional finalizada.
- Releases assinadas.
- SBOM e builds reproduzíveis.
- Auditoria externa.
- Teste de carga e fuzzing contínuo.
- Bootnodes operados por entidades independentes.
