# Quantum

Este documento detalha como iniciar a sua blockchain Pós-Quântica hiper-segura baseada no `Dilithium5` (Nível máximo de segurança do NIST) sem a necessidade de compilar bibliotecas complexas em C. Toda a segurança, certificados e chaves são gerados automaticamente!

---

## <span style="color:#2E86C1;">1. Iniciar com Dev Container (Recomendado)</span>

**Objetivo**: Rodar a blockchain em um ambiente Linux totalmente isolado e pronto, sem precisar instalar Python ou dependências na sua máquina local.

<div style="background-color:#F4F6F6; padding:10px; border-radius:5px;">
  <strong>Passo-a-passo</strong>:
  <ol>
    <li>Certifique-se de ter o <a href="https://www.docker.com/products/docker-desktop/" target="_blank">Docker</a> e o <a href="https://code.visualstudio.com/" target="_blank">VS Code</a> instalados.</li>
    <li>Instale a extensão <strong>Dev Containers</strong> no VS Code.</li>
    <li>Abra a pasta deste projeto (`Quantum`) no VS Code.</li>
    <li>Um alerta aparecerá no canto inferior direito: <strong>"Folder contains a Dev Container configuration file. Reopen folder to develop in a container."</strong>. Clique em <strong>Reopen in Container</strong>.</li>
    <li>Aguarde a construção. O VS Code instalará as dependências (`pip install -r requirements.txt`) automaticamente.</li>
  </ol>
</div>

---

## <span style="color:#2E86C1;">2. Executar a Blockchain no Container</span>

**Objetivo**: Iniciar o nó interativo da rede pós-quântica dentro do terminal do Dev Container.

<div style="background-color:#F4F6F6; padding:10px; border-radius:5px;">
  <strong>Comando (No terminal do VS Code dentro do Container)</strong>:
  <pre style="background-color:#E5E7E9; padding:10px; border-radius:5px;">
python Quantum.py
  </pre>
  <strong>Detalhes</strong>: 
  - A primeira execução irá gerar automaticamente um arquivo `config.yaml` com uma `db_key` hipersecreta (128 bytes reais de entropia).
  - Certificados SSL auto-assinados (`cert.pem` e `key.pem`) serão gerados para comunicação TLS (caso não existam).
  - O banco de dados criptografado usará Argon2 com custo extremo de memória (1GB).
</div>

---

## <span style="color:#2E86C1;">3. Conectando Nós Adicionais (Opcional)</span>

Para conectar outro nó na mesma rede, defina as variáveis de ambiente antes de rodar o `Quantum.py`:

<div style="background-color:#F4F6F6; padding:10px; border-radius:5px;">
  <strong>Comandos</strong>:
  <pre style="background-color:#E5E7E9; padding:10px; border-radius:5px;">
set "INITIAL_NODE=127.0.0.1:8000"
set "PORT=8001"
python Quantum.py
  </pre>
  <strong>Detalhes</strong>: O nó iniciará na porta 8001 e tentará sincronizar a chain via TLS com o nó inicial em 127.0.0.1:8000.
</div>

---

## <span style="color:#2E86C1;">Agressividade de Segurança Implementada</span>

- **Assinaturas:** `Dilithium5` (Maior nível de segurança pós-quântico do NIST para assinaturas digitais).
- **Armazenamento Seguro:** `ChaCha20Poly1305` + `Argon2id` com 1GB de custo de memória.
- **Rede:** Todo o tráfego P2P ocorre com encriptação TLS v1.2+ por padrão.
- **Isolamento:** A chave-mestra do banco de dados usa HKDF para derivar as chaves de encriptação, blindando qualquer dado em disco (ex: blocos, transações, e carteiras salvas).