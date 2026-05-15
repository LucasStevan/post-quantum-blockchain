<div align="center">
  <h1> Blockchain Post-Quantum Chain </h1>
  <p>Uma Prova de Conceito (PoC) 100% em Python de uma rede descentralizada resistente a ataques de computação quântica.</p>
</div>


<details>
  <summary><b>Índice</b></summary>
  <ul>
    <li><a href="#-sobre-o-projeto">Sobre o Projeto</a></li>
    <li><a href="#-segurança-e-criptografia">Segurança e Criptografia</a></li>
    <li><a href="#-iniciando-com-dev-container">Iniciando com Dev Container</a></li>
    <li><a href="#-executando-um-nó-único">Executando um Nó Único</a></li>
    <li><a href="#-configurando-uma-rede-multi-nó">Configurando uma Rede Multi-nó</a></li>
    <li><a href="#-verificando-a-sincronização">Verificando a Sincronização</a></li>
    <li><a href="#-avisos-importantes">Avisos Importantes</a></li>
  </ul>
</details>

---

## <span id="-sobre-o-projeto" style="color:#2E86C1;">Sobre o Projeto</span>

O **PQC-CHAIN** é uma implementação de blockchain pós-quântica hiper-segura baseada em assinaturas híbridas `ML-DSA-87` (FIPS 204, via liboqs) + `Ed25519` com verificação AND.

Este projeto foi desenhado para rodar em Dev Container: o ambiente compila e instala liboqs de forma reproduzível, evitando a implementação educacional `dilithium-py`. Toda a segurança, certificados TLS e chaves são gerados automaticamente!

---

## <span id="-segurança-e-criptografia" style="color:#2E86C1;">Segurança e Criptografia</span>

A agressividade da segurança implementada no PQC-CHAIN inclui:

<table style="width:100%; border-collapse: collapse; margin-bottom: 20px;">
  <tr style="background-color: #E8F8F5;">
    <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Componente</th>
    <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Tecnologia / Algoritmo</th>
    <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Descrição</th>
  </tr>
  <tr>
    <td style="padding: 10px; border: 1px solid #ddd;"><b>Assinaturas</b></td>
    <td style="padding: 10px; border: 1px solid #ddd;"><code>ML-DSA-87</code> + <code>Ed25519</code></td>
    <td style="padding: 10px; border: 1px solid #ddd;">Combiner híbrido com verificação AND: a transação só é válida se a assinatura pós-quântica e a assinatura clássica verificarem sobre o mesmo <code>tx_id</code>.</td>
  </tr>
  <tr>
    <td style="padding: 10px; border: 1px solid #ddd;"><b>Armazenamento</b></td>
    <td style="padding: 10px; border: 1px solid #ddd;"><code>ChaCha20Poly1305</code> + <code>Argon2id</code></td>
    <td style="padding: 10px; border: 1px solid #ddd;">Bancos de dados são criptografados na raiz com custo extremo de memória (1GB no Argon2id) para evitar ataques de força bruta.</td>
  </tr>
  <tr>
    <td style="padding: 10px; border: 1px solid #ddd;"><b>Rede P2P</b></td>
    <td style="padding: 10px; border: 1px solid #ddd;"><code>TLS v1.3+</code></td>
    <td style="padding: 10px; border: 1px solid #ddd;">Todo o tráfego P2P ocorre encriptado por padrão. Certificados auto-assinados são gerados dinamicamente na inicialização.</td>
  </tr>
  <tr>
    <td style="padding: 10px; border: 1px solid #ddd;"><b>Isolamento</b></td>
    <td style="padding: 10px; border: 1px solid #ddd;"><code>HKDF</code></td>
    <td style="padding: 10px; border: 1px solid #ddd;">A chave-mestra usa HKDF para derivar as chaves, blindando dados em disco (blocos, transações, carteiras).</td>
  </tr>
</table>

---

## <span id="-iniciando-com-dev-container" style="color:#2E86C1;">1. Iniciar com Dev Container (Recomendado)</span>

**Objetivo**: Rodar a blockchain em um ambiente Linux totalmente isolado, padronizado e pronto para uso, sem precisar poluir a máquina local com instalações de bibliotecas Python.

<div style="background-color:#F4F6F6; padding:15px; border-radius:8px; border-left: 5px solid #3498DB;">
  <h3 style="margin-top: 0;">🛠️ Passo-a-passo:</h3>
  <ol>
    <li>Certifique-se de ter o <a href="https://www.docker.com/products/docker-desktop/" target="_blank">Docker Desktop</a> e o <a href="https://code.visualstudio.com/" target="_blank">VS Code</a> instalados em seu computador.</li>
    <li>No VS Code, instale a extensão <strong>Dev Containers</strong> (desenvolvida pela Microsoft).</li>
    <li>Abra a pasta raiz deste projeto no VS Code.</li>
    <li>Um alerta aparecerá no canto inferior direito: <em>"Folder contains a Dev Container configuration file. Reopen folder to develop in a container."</em> Clique em <strong>Reopen in Container</strong>.</li>
    <li>Aguarde a construção. O VS Code preparará a imagem e instalará todas as dependências (<code>pip install -r requirements.txt</code>) automaticamente.</li>
  </ol>
</div>

---

## <span id="-executando-um-nó-único" style="color:#2E86C1;">2. Executar a Blockchain (Nó Único)</span>

**Objetivo**: Iniciar o nó interativo e criar o Gênesis da sua rede.

<div style="background-color:#F4F6F6; padding:15px; border-radius:8px; border-left: 5px solid #2ECC71;">
  <h3 style="margin-top: 0;"> Comando (No terminal dentro do Container):</h3>
  <pre style="background-color:#2C3E50; color:#ECF0F1; padding:15px; border-radius:5px; font-family: 'Courier New', Courier, monospace;"><code>python Quantum.py</code></pre>
  
  <h3> O que acontece na primeira execução?</h3>
  <ul>
    <li>O sistema detecta que não há arquivos de configuração.</li>
    <li>Gera automaticamente um arquivo <code>config.yaml</code> com uma <code>db_key</code> hipersecreta (128 bytes reais de entropia).</li>
    <li>Cria e salva certificados SSL auto-assinados (<code>cert.pem</code> e <code>key.pem</code>) para que outras conexões sejam seguras.</li>
    <li>Inicia o banco criptografado com Argon2 (processo requer cerca de 1GB de RAM momentânea).</li>
  </ul>
</div>

---

## <span id="-configurando-uma-rede-multi-nó" style="color:#2E86C1;">3. Configurando uma Rede Multi-nó</span>

Para simular uma rede descentralizada completa localmente, você pode instanciar vários nós em portas diferentes.

> ** IMPORTANTE - Isolamento de Diretórios:** 
> Se rodar múltiplos nós na mesma pasta raiz, eles causarão conflito de banco de dados (bloqueio de arquivo) e usarão a mesma chave/certificados. Para simular múltiplos nós corretamente, **você deve criar pastas separadas para cada nó** (ex: <code>node0/</code>, <code>node1/</code>, <code>node2/</code>), copiar os arquivos Python (ou o repositório) para elas, e rodar o <code>Quantum.py</code> separadamente dentro de cada diretório.

### A. Nó Inicial (Semente/Ponto de Entrada) - Porta 8004
Este será o nó principal ao qual os outros se conectarão para baixar o histórico inicial.

<div style="background-color:#F4F6F6; padding:15px; border-radius:8px; margin-bottom: 15px;">
  <p><strong>Terminal 0 (Dentro da pasta do Nó 0)</strong></p>
  <pre style="background-color:#2C3E50; color:#ECF0F1; padding:15px; border-radius:5px;"><code># No Windows PowerShell:
$env:PORT="8004"
python Quantum.py

# No Linux/Mac/DevContainer:
export PORT=8004
python Quantum.py</code></pre>
</div>

### B. Nó Adicional 1 - Porta 8001
Configurar o nó atual na porta 8001 para se sincronizar automaticamente com o nó inicial em 8004.

<div style="background-color:#F4F6F6; padding:15px; border-radius:8px; margin-bottom: 15px;">
  <p><strong>Terminal 1 (Dentro da pasta do Nó 1)</strong></p>
  <pre style="background-color:#2C3E50; color:#ECF0F1; padding:15px; border-radius:5px;"><code># No Windows PowerShell:
$env:INITIAL_NODE="127.0.0.1:8004"
$env:PORT="8001"
python Quantum.py

# No Linux/Mac/DevContainer:
export INITIAL_NODE="127.0.0.1:8004"
export PORT=8001
python Quantum.py</code></pre>
</div>

### C. Nó Adicional 2 - Porta 8002
Da mesma forma, podemos adicionar um terceiro nó.

<div style="background-color:#F4F6F6; padding:15px; border-radius:8px; margin-bottom: 15px;">
  <p><strong>Terminal 2 (Dentro da pasta do Nó 2)</strong></p>
  <pre style="background-color:#2C3E50; color:#ECF0F1; padding:15px; border-radius:5px;"><code># No Windows PowerShell:
$env:INITIAL_NODE="127.0.0.1:8004"
$env:PORT="8002"
python Quantum.py

# No Linux/Mac/DevContainer:
export INITIAL_NODE="127.0.0.1:8004"
export PORT=8002
python Quantum.py</code></pre>
</div>

---

## <span id="-verificando-a-sincronização" style="color:#2E86C1;">4. Verificando a Sincronização e P2P</span>

Depois de iniciar a rede, você pode interligar os nós mutuamente para formar uma malha (mesh) mais resiliente.

<div style="background-color:#FEF9E7; padding:15px; border-radius:8px; border-left: 5px solid #F1C40F;">
  <h3 style="margin-top: 0;"> Passos de Verificação:</h3>
  <ol>
    <li>No <b>Terminal 1</b> (nó 8001), selecione a opção <strong>8 ("Add peer")</strong> no menu interativo do console e adicione o IP: <code>127.0.0.1:8002</code>.</li>
    <li>No <b>Terminal 2</b> (nó 8002), use a mesma opção <strong>8</strong> para adicionar <code>127.0.0.1:8001</code>.</li>
    <li>Em qualquer nó, acesse a opção <strong>7 ("Network status")</strong>. Você verá a lista de peers conhecidos e as conexões ativas.</li>
    <li>O status do <code>Initial node</code> deve constar como <code>OK</code> e as conexões P2P devem mostrar tráfego seguro.</li>
  </ol>
</div>

---

## <span id="-avisos-importantes" style="color:#2E86C1;">5. Avisos Importantes</span>

- **Portas em Uso**: Antes de iniciar, certifique-se de que as portas `8001`, `8002`, `8004` (e `8000` se usada como padrão sem definição de porta) não estejam sendo ocupadas por outras aplicações.
- **Backups da Chave de DB**: Se perder o arquivo `config.yaml` ou a `db_key`, os dados locais da blockchain (blocos salvos localmente e a carteira) serão permanentemente inacessíveis. A criptografia é **inquebrável**.
- **Consumo de Memória**: Por design, o Argon2 consome ~1GB de RAM por breves momentos durante a decodificação da chave do banco. Isso garante resistência a ASICs e força bruta em caso de vazamento físico do arquivo do banco.
- **Replay Protection**: transações v2 incluem `PQC_CHAIN_ID` no `tx_id`. Redes, forks e testnets devem usar identificadores diferentes.
- **Modelo de Ameaças**: veja `readme-issue.md` para as correções das issues 1-3, comandos de execução e limites de segurança.

---

<div align="center" style="margin-top: 40px; color: #7F8C8D;">
  <i>Construído para a era da computação quântica. Desenvolvido com Python.</i>
</div>
