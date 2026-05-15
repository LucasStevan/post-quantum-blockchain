# Quantum.py - A Quantum-Resistant Blockchain Implementation
import asyncio
import json
import time
import logging
import uuid
import os
import re
import functools
import hashlib
import struct
import ctypes as ct
from threading import Lock
from typing import List, Dict, Optional, Tuple, Set
import click
import ssl
from cryptography.hazmat.primitives import hashes, hmac, serialization
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography import x509
from cryptography.x509.oid import NameOID
import datetime
import yaml
import zstandard as zstd
import argon2
import oqs
from mnemonic import Mnemonic
from rocksdict import Rdict, Options
import websockets
from websockets.server import serve
from concurrent.futures import ProcessPoolExecutor
from aiohttp import web
from wallet_store import load_wallet_data, save_wallet_data, wallet_store_exists

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
logging.getLogger('websockets').setLevel(logging.WARNING)

async def async_input(prompt: str = "") -> str:
    return await asyncio.get_event_loop().run_in_executor(None, functools.partial(input, prompt))

async def async_prompt(text: str, **kwargs) -> str:
    return await asyncio.get_event_loop().run_in_executor(None, functools.partial(click.prompt, text, **kwargs))

# Constants
DEFAULT_CHAIN_ID = "pqc-chain-mainnet-2026-ml-dsa-87-v2"
CHAIN_ID_ENV = "PQC_CHAIN_ID"
TX_HASH_DOMAIN = b"PQC-CHAIN:TX:v2"
DEFAULT_ML_DSA_ALGORITHM = "ML-DSA-87"
ML_DSA_ALGORITHM_ENV = "PQC_ML_DSA_ALGORITHM"
ED25519_PUBLIC_KEY_SIZE = 32
ED25519_SIGNATURE_SIZE = 64
ADDRESS_RE = re.compile(r"^[0-9a-f]{128}$")
COIN = 100_000_000
MAX_SUPPLY = 21_000_000 * COIN
INITIAL_BLOCK_REWARD = 50 * COIN
HALVING_INTERVAL = 55_000
TARGET_BLOCK_TIME = 60
DIFFICULTY_ADJUSTMENT_INTERVAL = 2000

# Binary difficulty: leading zero bits 

INITIAL_DIFFICULTY = 4  
GENESIS_HASH = '04d0a6dcd5ec2218b8180b9a456158f79abaa4fe731772e8dd3c2ae7fdba4f5ae71a7947f62d6471ab7cf67d76e3c81c5148df231b662424eae3a99d7c433fcb'
GENESIS_BLOCK_JSON = '{"index":0,"transactions":[{"tx_id":"43e04dcf531e13709658b276550c5eb7276e5f203d884fbadccede8c438f60af827c389c8b2711d5563784fcd2b778e6178df94de46f64116303fa66a8cdb40b","inputs":[],"outputs":[{"amount":5000000000,"address":"634518687b996f091d9467f1017e3e59419a3a447e7f0cfcf6d9ddb9cd105b13f05e646d9c5ebdc009f07837a6a215f19990e2b561ac30f5a1fdc31932188370"}],"is_coinbase":true,"timestamp":1778127229.4563112}],"previous_hash":"00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000","difficulty":4,"timestamp":1778127229.4563112,"nonce":45,"hash":"04d0a6dcd5ec2218b8180b9a456158f79abaa4fe731772e8dd3c2ae7fdba4f5ae71a7947f62d6471ab7cf67d76e3c81c5148df231b662424eae3a99d7c433fcb","merkle_root":"43e04dcf531e13709658b276550c5eb7276e5f203d884fbadccede8c438f60af827c389c8b2711d5563784fcd2b778e6178df94de46f64116303fa66a8cdb40b"}'
CONFIG_FILE = 'config.yaml'
PEER_CHECK_INTERVAL = 10

# Prune block bodies older than 100 blocks
PRUNE_DEPTH = 100 

# Security parameters & Network limits
NONCE_SIZE = 128
ARGON2_MEMORY_COST = 2**20
ARGON2_TIME_COST = 12
MAX_MEMPOOL_BYTES = 300 * 1024 * 1024
MAX_BLOCK_BYTES = 1 * 1024 * 1024
MAX_CONNECTIONS_PER_IP = 3

def compute_sha3_512(data: bytes) -> str:
    return hashlib.sha3_512(data).hexdigest()

def get_chain_id() -> str:
    chain_id = os.getenv(CHAIN_ID_ENV, DEFAULT_CHAIN_ID).strip()
    if not chain_id:
        raise ValueError(f"{CHAIN_ID_ENV} must not be empty.")
    return chain_id

def get_chain_id_bytes() -> bytes:
    return get_chain_id().encode("utf-8")

def _select_ml_dsa_algorithm() -> str:
    requested = os.getenv(ML_DSA_ALGORITHM_ENV)
    candidates = (requested,) if requested else (DEFAULT_ML_DSA_ALGORITHM,)
    enabled = set(oqs.get_enabled_sig_mechanisms())
    for candidate in candidates:
        if candidate and candidate in enabled:
            return candidate
    available = ", ".join(sorted(enabled))
    raise RuntimeError(
        f"No enabled ML-DSA signature mechanism found. Tried {candidates}. "
        f"Enabled liboqs signatures: {available}"
    )

ML_DSA_ALGORITHM = _select_ml_dsa_algorithm()

class MLDSA87:
    """Thin liboqs-backed ML-DSA facade used by the hybrid wallet."""

    algorithm = ML_DSA_ALGORITHM
    _rng_lock = Lock()
    _rng_callback_type = ct.CFUNCTYPE(None, ct.c_void_p, ct.c_size_t)
    _active_rng_callback = None

    with oqs.Signature(algorithm) as _sig_meta:
        public_key_size = int(_sig_meta.length_public_key)
        secret_key_size = int(_sig_meta.length_secret_key)
        signature_size = int(_sig_meta.length_signature)

    @staticmethod
    def _deterministic_rng(seed: bytes):
        stream_seed = hashlib.sha3_512(
            b"PQC-CHAIN:ML-DSA-87:keygen:v1:" + seed
        ).digest()
        counter = 0

        def rng(buffer, bytes_to_read):
            nonlocal counter
            size = int(bytes_to_read)
            out = bytearray()
            while len(out) < size:
                out.extend(hashlib.sha3_512(
                    stream_seed + counter.to_bytes(16, "big")
                ).digest())
                counter += 1
            ct.memmove(buffer, bytes(out[:size]), size)

        return rng

    @classmethod
    def keygen_from_seed(cls, seed: bytes) -> Tuple[bytes, bytes]:
        with cls._rng_lock:
            callback = cls._rng_callback_type(cls._deterministic_rng(seed))
            cls._active_rng_callback = callback
            oqs.native().OQS_randombytes_custom_algorithm.argtypes = [cls._rng_callback_type]
            oqs.native().OQS_randombytes_custom_algorithm.restype = None
            oqs.native().OQS_randombytes_switch_algorithm.argtypes = [ct.c_char_p]
            oqs.native().OQS_randombytes_switch_algorithm.restype = ct.c_int
            oqs.native().OQS_randombytes_custom_algorithm(callback)
            try:
                with oqs.Signature(cls.algorithm) as signer:
                    public_key = signer.generate_keypair()
                    secret_key = signer.export_secret_key()
                    return public_key, secret_key
            finally:
                oqs.native().OQS_randombytes_switch_algorithm(b"system")
                cls._active_rng_callback = None

    @classmethod
    def sign(cls, secret_key: bytes, message: bytes) -> bytes:
        if len(secret_key) != cls.secret_key_size:
            raise ValueError("Invalid ML-DSA secret key length.")
        with oqs.Signature(cls.algorithm, secret_key=secret_key) as signer:
            signature = signer.sign(message)
        if len(signature) != cls.signature_size:
            raise ValueError("Unexpected ML-DSA signature length.")
        return signature

    @classmethod
    def verify(cls, public_key: bytes, message: bytes, signature: bytes) -> bool:
        if len(public_key) != cls.public_key_size:
            return False
        if len(signature) != cls.signature_size:
            return False
        with oqs.Signature(cls.algorithm) as verifier:
            return verifier.verify(message, signature, public_key)

class EncryptedStorage:
    def __init__(self, db_key: str, storage_dir: str = "blockchain_data"):
        if len(db_key.encode()) < 128:
            raise ValueError("DB_KEY must be at least 128 bytes.")
        self.storage_dir = storage_dir
        deterministic_salt = hashlib.sha3_512(db_key.encode()).digest()[:32]
        hkdf = HKDF(
            algorithm=hashes.SHA3_512(),
            length=32,
            salt=deterministic_salt,
            info=b"storage-encryption-key",
            backend=default_backend()
        )
        self.key = hkdf.derive(db_key.encode())
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

    def _encrypt_data(self, data: bytes) -> bytes:
        chacha = ChaCha20Poly1305(self.key)
        nonce = os.urandom(12)
        return nonce + chacha.encrypt(nonce, data, None)

    def _decrypt_data(self, encrypted_data: bytes) -> bytes:
        if len(encrypted_data) < 12: raise ValueError("Invalid encrypted data.")
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        chacha = ChaCha20Poly1305(self.key)
        return chacha.decrypt(nonce, ciphertext, None)

    def save_bytes(self, filename: str, data: bytes):
        try:
            encrypted_data = self._encrypt_data(data)
            with open(os.path.join(self.storage_dir, filename), 'wb') as f:
                f.write(encrypted_data)
        except Exception as e:
            logger.error(f"Failed to save bytes to {filename}: {e}")

    def load_bytes(self, filename: str) -> bytes:
        filepath = os.path.join(self.storage_dir, filename)
        if not os.path.exists(filepath): return b""
        try:
            with open(filepath, 'rb') as f:
                encrypted_data = f.read()
            return self._decrypt_data(encrypted_data)
        except Exception as e:
            logger.error(f"Failed to load bytes from {filename}: {e}")
            return b""

    def save_data(self, filename: str, data: dict):
        try:
            compressed_data = zstd.compress(json.dumps(data).encode())
            encrypted_data = self._encrypt_data(compressed_data)
            with open(os.path.join(self.storage_dir, filename), 'wb') as f:
                f.write(encrypted_data)
        except Exception as e:
            logger.error(f"Failed to save data to {filename}: {e}")

    def load_data(self, filename: str) -> dict:
        filepath = os.path.join(self.storage_dir, filename)
        if not os.path.exists(filepath): return {}
        try:
            with open(filepath, 'rb') as f:
                encrypted_data = f.read()
            compressed_data = self._decrypt_data(encrypted_data)
            decompressed_data = zstd.decompress(compressed_data)
            return json.loads(decompressed_data.decode())
        except Exception as e:
            logger.error(f"Failed to load data from {filename}: {e}")
            return {}

class Configuration:
    def __init__(self):
        self.node = os.getenv('INITIAL_NODE', '127.0.0.1:8000')
        self.port = int(os.getenv('PORT', 8000))
        self.db_key = os.getenv('DB_KEY')
        self.storage_dir = os.getenv('STORAGE_DIR', f'blockchain_data_{self.port}')
        self.chain_id = os.getenv(CHAIN_ID_ENV, DEFAULT_CHAIN_ID)

    def load_yaml(self):
        config_changed = False
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir, exist_ok=True)
        self.config_path = os.path.join(self.storage_dir, 'config.yaml')
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f) or {}
                self.node = os.getenv('INITIAL_NODE') or config.get('node', self.node)
                self.port = int(os.getenv('PORT')) if os.getenv('PORT') else config.get('port', self.port)
                self.chain_id = os.getenv(CHAIN_ID_ENV) or config.get('chain_id', self.chain_id)
                if not self.db_key: self.db_key = config.get('db_key')
                if 'chain_id' not in config:
                    config_changed = True
        
        if not self.db_key or len(self.db_key.encode()) < 128:
            self.db_key = os.urandom(96).hex()
            os.environ['DB_KEY'] = self.db_key
            config_changed = True

        self.chain_id = self.chain_id.strip()
        if not self.chain_id:
            raise ValueError(f"{CHAIN_ID_ENV}/chain_id must not be empty.")
        os.environ[CHAIN_ID_ENV] = self.chain_id

        if config_changed or not os.path.exists(self.config_path):
            with open(self.config_path, 'w') as f:
                yaml.safe_dump({'node': self.node, 'port': self.port, 'db_key': self.db_key, 'chain_id': self.chain_id}, f)

class Wallet:
    def __init__(self, ml_pk: bytes, ed_pk: bytes, stored_key: bytes, address: str, salt: bytes, password_hash: bytes, ml_sk_raw: bytes = None, ed_sk_raw=None):
        self.ml_pk = ml_pk
        self.ed_pk = ed_pk
        self.public_key_hex = ml_pk.hex() + ":" + ed_pk.hex()
        self.stored_key = stored_key
        self.address = address
        self.salt = salt
        self.password_hash = password_hash
        self.ml_sk_raw = ml_sk_raw
        self.ed_sk_raw = ed_sk_raw
        
    @staticmethod
    def _generate_keys_from_seed(seed_bytes: bytes) -> tuple:
        ml_pk, ml_sk = MLDSA87.keygen_from_seed(seed_bytes)
        ed_sk = ed25519.Ed25519PrivateKey.from_private_bytes(seed_bytes)
        ed_pk = ed_sk.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        return ml_pk, ml_sk, ed_pk, ed_sk

    @staticmethod
    def create_new(password: str) -> tuple['Wallet', str]:
        if len(password) < 12: raise ValueError("Password must be at least 12 characters.")
        mnemo = Mnemonic("english")
        words = mnemo.generate(strength=256)
        seed_bytes = mnemo.to_seed(words, passphrase="")[:32]
        
        ml_pk, ml_sk, ed_pk, ed_sk = Wallet._generate_keys_from_seed(seed_bytes)
        address = compute_sha3_512(ml_pk + ed_pk)

        hasher = argon2.PasswordHasher(time_cost=ARGON2_TIME_COST, memory_cost=ARGON2_MEMORY_COST, parallelism=4, hash_len=32, salt_len=32, type=argon2.low_level.Type.ID)
        salt = os.urandom(32)
        password_hash = hasher.hash(password.encode(), salt=salt).encode()

        key = hasher.hash(password.encode(), salt=salt).encode()[:32]
        chacha = ChaCha20Poly1305(key)
        nonce = os.urandom(12)
        encrypted_seed = chacha.encrypt(nonce, seed_bytes, None)
        stored_key = salt + nonce + encrypted_seed

        return Wallet(ml_pk, ed_pk, stored_key, address, salt, password_hash, ml_sk, ed_sk), words

    @staticmethod
    def import_from_seed(words: str, password: str) -> 'Wallet':
        if len(password) < 12: raise ValueError("Password must be at least 12 characters.")
        mnemo = Mnemonic("english")
        if not mnemo.check(words): raise ValueError("Invalid seed phrase.")
        seed_bytes = mnemo.to_seed(words, passphrase="")[:32]
        
        ml_pk, ml_sk, ed_pk, ed_sk = Wallet._generate_keys_from_seed(seed_bytes)
        address = compute_sha3_512(ml_pk + ed_pk)

        hasher = argon2.PasswordHasher(time_cost=ARGON2_TIME_COST, memory_cost=ARGON2_MEMORY_COST, parallelism=4, hash_len=32, salt_len=32, type=argon2.low_level.Type.ID)
        salt = os.urandom(32)
        password_hash = hasher.hash(password.encode(), salt=salt).encode()

        key = hasher.hash(password.encode(), salt=salt).encode()[:32]
        chacha = ChaCha20Poly1305(key)
        nonce = os.urandom(12)
        encrypted_seed = chacha.encrypt(nonce, seed_bytes, None)
        stored_key = salt + nonce + encrypted_seed

        return Wallet(ml_pk, ed_pk, stored_key, address, salt, password_hash, ml_sk, ed_sk)

    @staticmethod
    async def load(address: str, password: str, storage: EncryptedStorage) -> Optional['Wallet']:
        wallets_data = load_wallet_data(storage)
        wallet_data = next((w for w in wallets_data.get("wallets", []) if w['address'] == address), None)
        if not wallet_data: return None

        stored_key = bytes.fromhex(wallet_data['private_key'])
        salt = bytes.fromhex(wallet_data['salt'])
        stored_hash = bytes.fromhex(wallet_data['password_hash'])

        hasher = argon2.PasswordHasher(time_cost=ARGON2_TIME_COST, memory_cost=ARGON2_MEMORY_COST, parallelism=4, hash_len=32, salt_len=32, type=argon2.low_level.Type.ID)
        try: hasher.verify(stored_hash, password.encode())
        except argon2.exceptions.VerificationError: return None

        nonce, encrypted_seed = stored_key[32:44], stored_key[44:]
        key = hasher.hash(password.encode(), salt=salt).encode()[:32]
        chacha = ChaCha20Poly1305(key)
        
        try:
            seed_bytes = chacha.decrypt(nonce, encrypted_seed, None)
            ml_pk, ml_sk, ed_pk, ed_sk = Wallet._generate_keys_from_seed(seed_bytes)
            return Wallet(ml_pk, ed_pk, stored_key, address, salt, stored_hash, ml_sk, ed_sk)
        except Exception: return None

    def sign(self, message: bytes) -> bytes:
        if not self.ml_sk_raw or not self.ed_sk_raw: raise ValueError("Private key not loaded in memory.")
        ml_sig = MLDSA87.sign(self.ml_sk_raw, message)
        ed_sig = self.ed_sk_raw.sign(message)
        return len(ml_sig).to_bytes(4, 'big') + ml_sig + ed_sig

    @staticmethod
    def verify_signature(ml_pk: bytes, ed_pk: bytes, message: bytes, signature: bytes) -> bool:
        try:
            if len(ml_pk) != MLDSA87.public_key_size or len(ed_pk) != ED25519_PUBLIC_KEY_SIZE:
                return False
            if len(signature) != 4 + MLDSA87.signature_size + ED25519_SIGNATURE_SIZE:
                return False
            ml_len = int.from_bytes(signature[:4], 'big')
            if ml_len != MLDSA87.signature_size:
                return False
            ml_sig = signature[4:4+ml_len]
            ed_sig = signature[4+ml_len:]
            
            if len(ed_sig) != ED25519_SIGNATURE_SIZE:
                return False
            if not MLDSA87.verify(ml_pk, message, ml_sig): return False
            ed_pub = ed25519.Ed25519PublicKey.from_public_bytes(ed_pk)
            ed_pub.verify(ed_sig, message)
            return True
        except Exception: return False

def verify_tx_signature_worker(ml_pk: bytes, ed_pk: bytes, tx_id_encoded: bytes, sig_bytes: bytes) -> bool:
    # Multiprocessing worker function
    return Wallet.verify_signature(ml_pk, ed_pk, tx_id_encoded, sig_bytes)

class TxOut:
    def __init__(self, amount: int, address: str, **kwargs):
        self.amount = amount
        self.address = address
    def to_dict(self): return {"amount": self.amount, "address": self.address}

class TxIn:
    def __init__(self, tx_id: str, out_idx: int, signature: str = "", pub_key: str = ""):
        self.tx_id = tx_id
        self.out_idx = out_idx
        self.signature = signature
        self.pub_key = pub_key
    def to_dict(self): return {"tx_id": self.tx_id, "out_idx": self.out_idx, "signature": self.signature, "pub_key": self.pub_key}

class Transaction:
    def __init__(self, inputs: List[TxIn], outputs: List[TxOut], is_coinbase: bool = False, tx_id: str = None, timestamp: float = None):
        self.inputs = inputs
        self.outputs = outputs
        self.is_coinbase = is_coinbase
        self.timestamp = time.time() if timestamp is None else timestamp
        self.fee = 0
        self.tx_id = tx_id or self.compute_hash()

    def compute_hash(self) -> str:
        data = bytearray()
        chain_id_b = get_chain_id_bytes()
        data.extend(struct.pack('>I', len(TX_HASH_DOMAIN)))
        data.extend(TX_HASH_DOMAIN)
        data.extend(struct.pack('>I', len(chain_id_b)))
        data.extend(chain_id_b)
        data.extend(struct.pack('?', self.is_coinbase))
        data.extend(struct.pack('>d', self.timestamp))
        for txin in self.inputs:
            tx_id_b = txin.tx_id.encode('utf-8')
            data.extend(struct.pack('>I', len(tx_id_b)))
            data.extend(tx_id_b)
            data.extend(struct.pack('>I', txin.out_idx))
        for txout in self.outputs:
            addr_b = txout.address.encode('utf-8')
            data.extend(struct.pack('>Q', txout.amount))
            data.extend(struct.pack('>I', len(addr_b)))
            data.extend(addr_b)
        return compute_sha3_512(bytes(data))

    def has_valid_id(self) -> bool:
        return self.tx_id == self.compute_hash()

    def has_valid_outputs(self) -> bool:
        if not self.outputs:
            return False
        for txout in self.outputs:
            if type(txout.amount) is not int or txout.amount <= 0 or txout.amount > MAX_SUPPLY:
                return False
            if not ADDRESS_RE.fullmatch(txout.address):
                return False
        return True

    def to_dict(self):
        return {
            "tx_id": self.tx_id, "inputs": [i.to_dict() for i in self.inputs],
            "outputs": [o.to_dict() for o in self.outputs], "is_coinbase": self.is_coinbase, "timestamp": self.timestamp
        }

    @staticmethod
    def from_dict(d: dict):
        inputs = [TxIn(i['tx_id'], i['out_idx'], i['signature'], i['pub_key']) for i in d['inputs']]
        outputs = [TxOut(o['amount'], o['address']) for o in d['outputs']]
        return Transaction(inputs, outputs, d.get('is_coinbase', False), d['tx_id'], d['timestamp'])

class Block:
    def __init__(self, index: int, transactions: List[Transaction], previous_hash: str, difficulty: int, timestamp: float = None, nonce: int = 0, hash: str = None, merkle_root: str = None):
        self.index = index
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.difficulty = difficulty
        self.timestamp = time.time() if timestamp is None else timestamp
        self.nonce = nonce
        self.merkle_root = merkle_root or self.compute_merkle_root()
        self.hash = hash or self.compute_hash()

    def compute_merkle_root(self) -> str:
        if not self.transactions: return ""
        tx_hashes = [tx.tx_id for tx in self.transactions]
        while len(tx_hashes) > 1:
            if len(tx_hashes) % 2 != 0: tx_hashes.append(tx_hashes[-1])
            tx_hashes = [compute_sha3_512((tx_hashes[i] + tx_hashes[i+1]).encode()) for i in range(0, len(tx_hashes), 2)]
        return tx_hashes[0]

    def compute_hash(self) -> str:
        data = f"{self.index}{self.previous_hash}{self.timestamp}{self.nonce}{self.difficulty}{self.merkle_root}"
        return compute_sha3_512(data.encode())

    async def mine(self):
        target = (1 << 512) - 1 >> self.difficulty
        start_time = time.time()
        while int(self.hash, 16) > target:
            self.nonce += 1
            self.hash = self.compute_hash()
            if self.nonce % 10000 == 0: await asyncio.sleep(0)
        logger.info(f"Block {self.index} mined in {time.time() - start_time:.2f} seconds")
        return True

    def to_dict(self):
        return {
            "index": self.index, "transactions": [tx.to_dict() for tx in self.transactions],
            "previous_hash": self.previous_hash, "difficulty": self.difficulty,
            "timestamp": self.timestamp, "nonce": self.nonce, "hash": self.hash,
            "merkle_root": self.merkle_root
        }

    @staticmethod
    def from_dict(d: dict):
        txs = [Transaction.from_dict(tx) for tx in d['transactions']]
        return Block(d['index'], txs, d['previous_hash'], d['difficulty'], d['timestamp'], d['nonce'], d.get('hash'), d.get('merkle_root'))

class Blockchain:
    def __init__(self, storage: EncryptedStorage, host: str, port: int):
        self.storage = storage
        self.db = Rdict(os.path.join(storage.storage_dir, "rocks_db"))
        self.mempool: List[Transaction] = []
        for key in self.db.keys():
            if key.startswith(b'mempool:'):
                data = self.db.get(key)
                self.mempool.append(Transaction.from_dict(json.loads(zstd.decompress(data).decode())))
        self.mempool.sort(key=lambda t: getattr(t, 'fee', 0), reverse=True)
        
        self.difficulty = INITIAL_DIFFICULTY
        self.peers: set = set()
        self.banned_peers: set = set()
        self.active_connections = {}
        self.running = True
        self.host = host
        self.port = port
        self.own_address = f"{host}:{port}"
        self.node_key = ed25519.Ed25519PrivateKey.generate()
        self.node_pub_hex = self.node_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()

        self.client_ctx = ssl.create_default_context()
        self.client_ctx.check_hostname = False
        self.client_ctx.verify_mode = ssl.CERT_NONE
        self.client_ctx.minimum_version = ssl.TLSVersion.TLSv1_3
        
        # Load chain state
        self.height = int(self.db.get(b'chain:height', b'0').decode())
        self.latest_hash = self.db.get(b'chain:latest_hash', GENESIS_HASH.encode()).decode()

        # Hardcoded Genesis injection if empty
        if self.height == 0:
            gen = self.get_block_by_height(0)
            if not gen:
                gen = Block.from_dict(json.loads(GENESIS_BLOCK_JSON))
                self.db[f'block:{gen.hash}'.encode()] = zstd.compress(json.dumps(gen.to_dict()).encode())
                self.db[f'height:{gen.index}'.encode()] = gen.hash.encode()
                for i, txout in enumerate(gen.transactions[0].outputs):
                    self.add_utxo(gen.transactions[0].tx_id, i, txout, gen.index)
            self.latest_hash = gen.hash
            self.db[b'chain:height'] = b'0'
            self.db[b'chain:latest_hash'] = self.latest_hash.encode()

    async def initialize(self):
        pass

    def get_reward(self, block_index: int, prev_hash: str, difficulty: int) -> int:
        halvings = block_index // HALVING_INTERVAL
        if halvings >= 64: return 0
        if block_index == 0:
            return INITIAL_BLOCK_REWARD
        entropy = (int(prev_hash[-4:], 16) % 20) + 1  
        reward = (entropy * difficulty) * (COIN // 2)
        return reward >> halvings

    def get_next_difficulty(self) -> int:
        if self.height < 1:
            return INITIAL_DIFFICULTY
        
        prev_block = self.get_block_by_hash(self.latest_hash)
        if not prev_block: return INITIAL_DIFFICULTY
        
        # stability
        blocks_to_avg = min(10, self.height)
        old_block = self.get_block_by_height(self.height - blocks_to_avg)
        
        if not old_block: 
            return prev_block.difficulty
            
        avg_time = (prev_block.timestamp - old_block.timestamp) / blocks_to_avg
        current_diff = prev_block.difficulty
        
        if avg_time < TARGET_BLOCK_TIME * 0.75:
            return current_diff + 1
        elif avg_time > TARGET_BLOCK_TIME * 1.5:
            return max(1, current_diff - 1)
        return current_diff

    def get_block_by_hash(self, hash: str) -> Optional[Block]:
        data = self.db.get(f'block:{hash}'.encode())
        if not data: return None
        return Block.from_dict(json.loads(zstd.decompress(data).decode()))
        
    def get_block_by_height(self, height: int) -> Optional[Block]:
        h = self.db.get(f'height:{height}'.encode())
        if not h: return None
        return self.get_block_by_hash(h.decode())

    def add_utxo(self, tx_id: str, index: int, txout: TxOut, block_height: int):
        data = txout.to_dict()
        data['block_height'] = block_height
        self.db[f'c:{tx_id}:{index}'.encode()] = zstd.compress(json.dumps(data).encode())
        
    def remove_utxo(self, tx_id: str, index: int):
        key = f'c:{tx_id}:{index}'.encode()
        if key in self.db:
            del self.db[key]
            
    def get_utxo(self, tx_id: str, index: int) -> Optional[TxOut]:
        data = self.db.get(f'c:{tx_id}:{index}'.encode())
        if data:
            return TxOut(**json.loads(zstd.decompress(data).decode()))
        return None

    def find_utxos_for_amount(self, address: str, amount: int) -> Tuple[int, List[Tuple[str, int]]]:
        gathered = 0
        inputs_info = []
        for key in self.db.keys():
            if key.startswith(b'c:'):
                data = self.db.get(key)
                utxo = TxOut(**json.loads(zstd.decompress(data).decode()))
                if utxo.address == address:
                    gathered += utxo.amount
                    parts = key.decode().split(':')
                    inputs_info.append((parts[1], int(parts[2])))
                    if gathered >= amount: break
        return gathered, inputs_info

    def get_balance_details(self, address: str, req_conf: int = 10) -> Tuple[int, int, Dict[str, Tuple[int, int]]]:
        available = 0
        pending = 0
        validating = {}

        for key in self.db.keys():
            if key.startswith(b'c:'):
                data = self.db.get(key)
                d = json.loads(zstd.decompress(data).decode())
                h = d.get('block_height', 0)
                utxo = TxOut(**d)
                if utxo.address == address:
                    parts = key.decode().split(':')
                    tx_id = parts[1]
                    depth = self.height - h + 1
                    if depth >= req_conf:
                        available += utxo.amount
                    else:
                        pending += utxo.amount
                        validating[tx_id] = (utxo.amount, depth) 

        for tx in self.mempool:
            for txin in tx.inputs:
                utxo = self.get_utxo(txin.tx_id, txin.out_idx)
                if utxo and utxo.address == address:
                    available -= utxo.amount
            for out in tx.outputs:
                if out.address == address:
                    pending += out.amount
                    validating[tx.tx_id] = (out.amount, 0)
                    
        return available, pending, validating

    def is_valid_transaction(self, tx: Transaction) -> bool:
        if not tx.has_valid_id() or not tx.has_valid_outputs():
            return False
        if tx.is_coinbase: return True
        if not tx.inputs:
            return False
        input_sum = 0
        seen_inputs = set()
        
        
        futures = []
        with ProcessPoolExecutor() as executor:
            for txin in tx.inputs:
                outpoint = f"{txin.tx_id}:{txin.out_idx}"
                if outpoint in seen_inputs:
                    return False
                seen_inputs.add(outpoint)
                utxo = self.get_utxo(txin.tx_id, txin.out_idx)
                if not utxo: return False
                input_sum += utxo.amount
                
                pub_keys = txin.pub_key.split(':')
                if len(pub_keys) != 2: return False
                try:
                    ml_pk = bytes.fromhex(pub_keys[0])
                    ed_pk = bytes.fromhex(pub_keys[1])
                    sig_bytes = bytes.fromhex(txin.signature)
                except ValueError:
                    return False
                
                if compute_sha3_512(ml_pk + ed_pk) != utxo.address: return False
                
                futures.append(executor.submit(verify_tx_signature_worker, ml_pk, ed_pk, tx.tx_id.encode(), sig_bytes))
                
            if any(not f.result() for f in futures):
                return False
                
        output_sum = sum(out.amount for out in tx.outputs)
        if input_sum < output_sum: return False
        
        tx.fee = input_sum - output_sum
        return True

    def create_transaction(self, sender_wallet: Wallet, receiver_address: str, amount: int, fee: int = 0, req_conf: int = 10) -> Optional[Transaction]:
        if type(amount) is not int or type(fee) is not int or amount <= 0 or fee < 0:
            logger.error("Invalid amount or fee.")
            return None
        if not ADDRESS_RE.fullmatch(receiver_address):
            logger.error("Invalid receiver address.")
            return None
        mempool_used = set()
        for t in self.mempool:
            for txin in t.inputs:
                mempool_used.add(f"{txin.tx_id}:{txin.out_idx}")

        total_required = amount + fee
        gathered = 0
        inputs_info = []
        
        for key in self.db.keys():
            if key.startswith(b'c:'):
                parts = key.decode().split(':')
                tx_id, index = parts[1], int(parts[2])
                if f"{tx_id}:{index}" in mempool_used: continue
                
                data = self.db.get(key)
                d = json.loads(zstd.decompress(data).decode())
                h = d.get('block_height', 0)
                depth = self.height - h + 1
                if depth < req_conf: continue
                
                utxo = TxOut(**d)
                if utxo.address == sender_wallet.address:
                    gathered += utxo.amount
                    inputs_info.append((tx_id, index))
                    if gathered >= total_required: break

        if gathered < total_required:
            logger.error("Insufficient balance.")
            return None
            
        inputs = [TxIn(tx_id, out_idx) for tx_id, out_idx in inputs_info]
        outputs = [TxOut(amount, receiver_address)]
        if gathered > total_required: outputs.append(TxOut(gathered - total_required, sender_wallet.address))
            
        tx = Transaction(inputs, outputs)
        for txin in tx.inputs:
            txin.pub_key = sender_wallet.public_key_hex
            txin.signature = sender_wallet.sign(tx.tx_id.encode()).hex()
            
        tx.fee = fee
        return tx

    def add_to_mempool(self, tx: Transaction):
        if not self.is_valid_transaction(tx): return
        if tx.tx_id in [t.tx_id for t in self.mempool]: return
        self.mempool.append(tx)
        self.mempool.sort(key=lambda t: getattr(t, 'fee', 0), reverse=True)
        self.db[f'mempool:{tx.tx_id}'.encode()] = zstd.compress(json.dumps(tx.to_dict()).encode())
        while sum(len(json.dumps(t.to_dict()).encode()) for t in self.mempool) > MAX_MEMPOOL_BYTES and self.mempool:
            evicted = self.mempool.pop()
            key = f'mempool:{evicted.tx_id}'.encode()
            if key in self.db: del self.db[key]

    def get_txs_for_block(self) -> List[Transaction]:
        txs = []
        current_size = 0
        for tx in self.mempool:
            tx_size = len(json.dumps(tx.to_dict()).encode())
            if current_size + tx_size > MAX_BLOCK_BYTES - 1024: break
            txs.append(tx)
            current_size += tx_size
        return txs

    async def add_block(self, block: Block, broadcast: bool = True) -> bool:
        if self.db.get(f'block:{block.hash}'.encode()): return True
        
        if block.index == 0 and self.get_block_by_height(0):
            return False
            
        is_main_chain = True
        if block.index > 0:
            prev_block = self.get_block_by_hash(block.previous_hash)
            if not prev_block: 
                logger.warning(f"Orphan block received at index {block.index}. Missing parent.")
                return False
            if block.index != prev_block.index + 1:
                return False
                
            if block.previous_hash != self.latest_hash:
                if block.index <= self.height:
                    # Fork is shorter or equal, just store it but don't reorg
                    is_main_chain = False
                else:
                    # Fork is longer! We should initiate a REORG.
                    # Implementing a full UTXO rollback is complex. For now, we accept it as the new main chain.
                    logger.warning(f"CHAIN REORG DETECTED! Fork is longer ({block.index} > {self.height}).")
                    is_main_chain = True

            if block.merkle_root != block.compute_merkle_root():
                return False
            if block.hash != block.compute_hash():
                return False
            target = (1 << 512) - 1 >> block.difficulty
            if int(block.hash, 16) > target: return False
            if not block.transactions or not block.transactions[0].is_coinbase:
                return False
            if any(tx.is_coinbase for tx in block.transactions[1:]):
                return False

        if len(json.dumps(block.to_dict()).encode()) > MAX_BLOCK_BYTES: return False

        # Verify all block transactions with multiprocessing
        futures = []
        total_fees = 0
        spent_inputs = set()
        with ProcessPoolExecutor() as executor:
            for tx in block.transactions:
                if block.index > 0 and (not tx.has_valid_id() or not tx.has_valid_outputs()):
                    return False
                if tx.is_coinbase: continue
                if not tx.inputs:
                    return False
                input_sum = 0
                for txin in tx.inputs:
                    outpoint = f"{txin.tx_id}:{txin.out_idx}"
                    if outpoint in spent_inputs:
                        return False
                    spent_inputs.add(outpoint)
                    utxo = self.get_utxo(txin.tx_id, txin.out_idx)
                    if not utxo: return False
                    input_sum += utxo.amount
                    pub_keys = txin.pub_key.split(':')
                    if len(pub_keys) != 2: return False
                    try:
                        ml_pk, ed_pk = bytes.fromhex(pub_keys[0]), bytes.fromhex(pub_keys[1])
                        sig_bytes = bytes.fromhex(txin.signature)
                    except ValueError:
                        return False
                    if compute_sha3_512(ml_pk + ed_pk) != utxo.address: return False
                    futures.append(executor.submit(verify_tx_signature_worker, ml_pk, ed_pk, tx.tx_id.encode(), sig_bytes))
                output_sum = sum(out.amount for out in tx.outputs)
                if input_sum < output_sum: return False
                total_fees += input_sum - output_sum
                
            if any(not f.result() for f in futures):
                return False

        if block.index > 0:
            coinbase_sum = sum(out.amount for out in block.transactions[0].outputs)
            expected_reward = self.get_reward(block.index, block.previous_hash, block.difficulty)
            if coinbase_sum > expected_reward + total_fees:
                return False

        # Apply state changes
        for tx in block.transactions:
            for txin in tx.inputs:
                if not tx.is_coinbase: self.remove_utxo(txin.tx_id, txin.out_idx)
            for i, txout in enumerate(tx.outputs):
                self.add_utxo(tx.tx_id, i, txout, block.index)
                
        # Save block to DB
        self.db[f'block:{block.hash}'.encode()] = zstd.compress(json.dumps(block.to_dict()).encode())
        
        if is_main_chain:
            self.db[f'height:{block.index}'.encode()] = block.hash.encode()
            self.height = block.index
            self.latest_hash = block.hash
            self.db[b'chain:height'] = str(self.height).encode()
            self.db[b'chain:latest_hash'] = self.latest_hash.encode()
        
        # Remove from mempool and DB
        block_tx_ids = [t.tx_id for t in block.transactions]
        new_mempool = []
        for tx in self.mempool:
            if tx.tx_id in block_tx_ids:
                key = f'mempool:{tx.tx_id}'.encode()
                if key in self.db: del self.db[key]
            else:
                new_mempool.append(tx)
        self.mempool = new_mempool
        
        self.prune_old_blocks()
        
        if broadcast:
            asyncio.create_task(self.broadcast_block(block))
        return True

    def prune_old_blocks(self):
        if self.height > PRUNE_DEPTH:
            prune_height = self.height - PRUNE_DEPTH
            h = self.db.get(f'height:{prune_height}'.encode())
            if h:
                block_data = self.db.get(f'block:{h.decode()}'.encode())
                if block_data:
                    block_dict = json.loads(zstd.decompress(block_data).decode())
                    if block_dict.get('transactions'):
                        block_dict['transactions'] = [] # Prune bodies
                        self.db[f'block:{h.decode()}'.encode()] = zstd.compress(json.dumps(block_dict).encode())
                        logger.info(f"Pruned block body for height {prune_height}")

    # P2P Network Methods (WebSockets)
    async def _send_to_peer(self, peer: str, payload: bytes):
        if peer not in self.active_connections:
            try:
                ws = await websockets.connect(f"wss://{peer}", ssl=self.client_ctx)
                self.active_connections[peer] = ws
                asyncio.create_task(self.listen_to_peer(peer, ws))
            except Exception:
                return False
        try:
            await self.active_connections[peer].send(payload)
            return True
        except Exception:
            self.active_connections.pop(peer, None)
            return False

    async def broadcast_tx(self, tx: Transaction):
        payload = b'\x01' + zstd.compress(json.dumps(tx.to_dict()).encode())
        for peer in self.peers.copy():
            await self._send_to_peer(peer, payload)

    async def broadcast_block(self, block: Block):
        payload = b'\x02' + zstd.compress(json.dumps(block.to_dict()).encode())
        for peer in self.peers.copy():
            await self._send_to_peer(peer, payload)

    async def register_peer(self, node: str):
        if node not in self.peers and node != self.own_address and node not in self.banned_peers:
            self.peers.add(node)
            ts = time.time()
            msg = f"{self.own_address}:{get_chain_id()}:{ts}".encode()
            sig = self.node_key.sign(msg)
            handshake = {"peer": self.own_address, "pub_key": self.node_pub_hex, "signature": sig.hex(), "timestamp": ts, "chain_id": get_chain_id()}
            payload = b'\x03' + json.dumps(handshake).encode()
            await self._send_to_peer(node, payload)

    async def sync_chain(self, node: str):
        if node in self.banned_peers: return False
        req_height = self.height
        if self.height == 0 and not self.get_block_by_height(0):
            req_height = -1
        payload = b'\x04' + str(req_height).encode()
        await self._send_to_peer(node, payload)

    async def peer_monitor(self):
        while self.running:
            for peer in list(self.peers):
                await self.sync_chain(peer)
            await asyncio.sleep(PEER_CHECK_INTERVAL)

    async def handle_websocket(self, websocket):
        peer = websocket.remote_address[0] if websocket.remote_address else "unknown"
        try:
            async for message in websocket:
                msg_type = message[0]
                payload = message[1:]
                
                if msg_type == 1:
                    tx_data = json.loads(zstd.decompress(payload).decode())
                    tx = Transaction.from_dict(tx_data)
                    if tx.tx_id not in [t.tx_id for t in self.mempool] and self.is_valid_transaction(tx):
                        self.add_to_mempool(tx)
                        asyncio.create_task(self.broadcast_tx(tx))
                        
                elif msg_type == 2:
                    block_data = json.loads(zstd.decompress(payload).decode())
                    block = Block.from_dict(block_data)
                    if await self.add_block(block, broadcast=False):
                        asyncio.create_task(self.broadcast_block(block))
                        
                elif msg_type == 3: 
                    data = json.loads(payload.decode())
                    req_peer = data.get("peer")
                    if req_peer in self.banned_peers: continue
                    if data.get("chain_id") != get_chain_id():
                        self.banned_peers.add(req_peer)
                        continue
                    pub_hex, sig_hex, ts = data.get("pub_key"), data.get("signature"), data.get("timestamp")
                    if abs(time.time() - ts) > 60: continue
                    try:
                        ed_pub = ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub_hex))
                        ed_pub.verify(bytes.fromhex(sig_hex), f"{req_peer}:{data.get('chain_id')}:{ts}".encode())
                        if req_peer and req_peer != self.own_address:
                            self.peers.add(req_peer)
                    except Exception:
                        self.banned_peers.add(req_peer)
                        
                elif msg_type == 4:
                    peer_height = int(payload.decode())
                    if peer_height < self.height:
                        for h in range(peer_height + 1, self.height + 1):
                            block = self.get_block_by_height(h)
                            if block:
                                await websocket.send(b'\x02' + zstd.compress(json.dumps(block.to_dict()).encode()))
                                
        except websockets.exceptions.ConnectionClosed:
            pass

    async def listen_to_peer(self, peer: str, websocket):
        await self.handle_websocket(websocket)

def generate_self_signed_cert(storage_dir: str) -> ssl.SSLContext:
    cert_path = os.path.join(storage_dir, "cert.pem")
    key_path = os.path.join(storage_dir, "key.pem")
    if not os.path.exists(cert_path) or not os.path.exists(key_path):
        key = ed25519.Ed25519PrivateKey.generate()
        subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, u"PQCNode")])
        now = datetime.datetime.now(datetime.UTC)
        cert = x509.CertificateBuilder().subject_name(subject).issuer_name(issuer).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now).not_valid_after(now + datetime.timedelta(days=3650)).sign(key, None, default_backend())
        with open(key_path, "wb") as f:
            f.write(key.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.PKCS8, encryption_algorithm=serialization.NoEncryption()))
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile=cert_path, keyfile=key_path)
    context.minimum_version = ssl.TLSVersion.TLSv1_3
    return context

async def start_explorer_api(blockchain: Blockchain, host: str, port: int):
    app = web.Application()
    def cors():
        return {'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type'}
    
    async def get_blocks(request):
        try:
            page = int(request.query.get('page', 1))
            limit = int(request.query.get('limit', 20))
        except ValueError:
            page = 1
            limit = 20
            
        blocks = []
        end_height = blockchain.height - ((page - 1) * limit)
        start_height = max(0, end_height - limit + 1)
        
        for h in range(start_height, end_height + 1):
            b = blockchain.get_block_by_height(h)
            if b: blocks.append(b.to_dict())
            
        return web.json_response({
            'blocks': blocks,
            'total_blocks': blockchain.height + 1,
            'page': page,
            'limit': limit
        }, headers=cors())
        
    async def get_block(request):
        q = request.match_info['query']
        b = None
        try: b = blockchain.get_block_by_height(int(q))
        except: b = blockchain.get_block_by_hash(q)
        if b: return web.json_response(b.to_dict(), headers=cors())
        return web.json_response({'error':'not found'}, status=404, headers=cors())
        
    async def get_tx(request):
        txid = request.match_info['txid']
        for h in range(blockchain.height, max(-1, blockchain.height - 1000), -1):
            b = blockchain.get_block_by_height(h)
            if not b: continue
            for tx in b.transactions:
                if tx.tx_id == txid: return web.json_response(tx.to_dict(), headers=cors())
        for tx in blockchain.mempool:
            if tx.tx_id == txid: return web.json_response(tx.to_dict(), headers=cors())
        return web.json_response({'error':'not found'}, status=404, headers=cors())
        
    async def options(request): return web.Response(headers=cors())
    
    app.router.add_get('/api/blocks', get_blocks)
    app.router.add_get('/api/block/{query}', get_block)
    app.router.add_get('/api/tx/{txid}', get_tx)
    app.router.add_options('/api/{tail:.*}', options)
    
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    return runner

async def start_server(host: str, port: int, blockchain: Blockchain):
    ssl_ctx = generate_self_signed_cert(blockchain.storage.storage_dir)
    server = await serve(blockchain.handle_websocket, host, port, ssl=ssl_ctx)
    return server

async def interactive_loop(blockchain: Blockchain, storage: EncryptedStorage, config: Configuration):
    active_wallet = None
    print("\n[+] PQC Node Started")
    if not wallet_store_exists(storage):
        while True:
            print("\nDo you want to:")
            print("1. Create a new wallet")
            print("2. Use an existing wallet")
            choice = await async_input("> ")
            if choice == '1':
                pwd = await async_prompt("Enter new password (min 12 chars)", hide_input=False, confirmation_prompt=True)
                active_wallet, words = Wallet.create_new(pwd)
                save_wallet_data(storage, {"wallets": [{"address": active_wallet.address, "public_key": active_wallet.public_key_hex, "private_key": active_wallet.stored_key.hex(), "salt": active_wallet.salt.hex(), "password_hash": active_wallet.password_hash.hex()}]})
                print(f"\n[!] SAVE THESE 24 WORDS: {words}")
                print(f"[!] Address: {active_wallet.address}\n")
                break
            elif choice == '2':
                words = await async_input("Enter 12/24-word seed: ")
                pwd = await async_prompt("Enter new password for local storage", hide_input=False)
                try:
                    active_wallet = Wallet.import_from_seed(words.strip(), pwd)
                    save_wallet_data(storage, {"wallets": [{"address": active_wallet.address, "public_key": active_wallet.public_key_hex, "private_key": active_wallet.stored_key.hex(), "salt": active_wallet.salt.hex(), "password_hash": active_wallet.password_hash.hex()}]})
                    print(f"Wallet imported: {active_wallet.address}")
                    break
                except Exception as e: print(f"Error: {e}")
    else:
        wallets_data = load_wallet_data(storage)
        if wallets_data.get("wallets"):
            addr = wallets_data["wallets"][0]["address"]
            pwd = await async_prompt(f"Enter password to unlock wallet {addr[:8]}...", hide_input=False)
            active_wallet = await Wallet.load(addr, pwd, storage)
            if not active_wallet:
                print("Failed to unlock wallet. Exiting.")
                return



    while True:
        conf_bal, pend_bal, validating_txs = blockchain.get_balance_details(active_wallet.address) if active_wallet else (0,0,{})
        print(f"\n PQC | Height: {blockchain.height} | Confirmed: {conf_bal/COIN:.8f} PQC | Pending: {pend_bal/COIN:.8f} PQC")
        print("1. Send tokens")
        print("2. Mine block")
        print("3. Network status")
        print("4. Explorer (Blocks/Txs)")
        print("5. Exit")
        choice = (await async_input("> ")).strip()

        if choice == '1':
            rec = await async_input("Receiver address: ")
            amt_str = await async_input("Amount (PQC): ")
            try:
                amt = int(float(amt_str) * COIN)
                fee = int(0.0001 * COIN)
                tx = blockchain.create_transaction(active_wallet, rec, amt, fee)
                if tx:
                    blockchain.add_to_mempool(tx)
                    asyncio.create_task(blockchain.broadcast_tx(tx))
                    print(f"Transaction {tx.tx_id} broadcasted (Fee: 0.0001 PQC)!")
            except ValueError:
                print("Invalid amount.")
        elif choice == '2':
            if blockchain.height == 0 and not blockchain.get_block_by_height(0):
                print("Cannot mine! Wait for Genesis Block synchronization.")
                continue
            next_diff = blockchain.get_next_difficulty()
            prev = blockchain.latest_hash
            reward = blockchain.get_reward(blockchain.height + 1, prev, next_diff)
            txs_for_block = blockchain.get_txs_for_block()
            total_fees = sum(getattr(tx, 'fee', 0) for tx in txs_for_block)
            cb_tx = Transaction([], [TxOut(reward + total_fees, active_wallet.address)], is_coinbase=True)
            txs = [cb_tx] + txs_for_block
            block = Block(blockchain.height + 1, txs, prev, next_diff)
            print(f"Mining block with {len(txs_for_block)} txs (Reward: {reward/COIN:.8f} PQC | Fees: {total_fees/COIN:.8f} PQC)...")
            if await block.mine():
                await blockchain.add_block(block)
                print(f"Block {block.index} added. Hash: {block.hash}")
                print(f"Coinbase TxID (Miner Reward): {cb_tx.tx_id}")
        elif choice == '3':
            print(f"Chain height: {blockchain.height}")
            print(f"Mempool size: {len(blockchain.mempool)} txs ({sum(len(json.dumps(t.to_dict()).encode()) for t in blockchain.mempool)/1024:.2f} KB)")
            print(f"Connected Peers: {len(blockchain.peers)}")
            print(f"Banned Peers: {len(blockchain.banned_peers)}")
        elif choice == '4':
            query = (await async_input("Enter Block Height or TxID: ")).strip()
            try:
                h = int(query)
                b = blockchain.get_block_by_height(h)
                if b:
                    print(f"\n--- Block {b.index} ---")
                    print(f"Hash: {b.hash}")
                    print(f"Prev Hash: {b.previous_hash}")
                    print(f"Difficulty: {b.difficulty}")
                    print(f"Merkle Root: {b.merkle_root}")
                    print(f"Transactions: {len(b.transactions)}")
                else: print("Block not found.")
            except:
                print("Explorer Tx search simplified for refactor. Use the Web Explorer!")
        elif choice == '5':
            blockchain.running = False
            break

async def main():
    config = Configuration()
    config.load_yaml()
    storage = EncryptedStorage(config.db_key, config.storage_dir)
    blockchain = Blockchain(storage, '127.0.0.1', config.port)
    await blockchain.initialize()
    
    if config.node != blockchain.own_address:
        await blockchain.register_peer(config.node)
        await blockchain.sync_chain(config.node)
        
    server = await start_server('0.0.0.0', config.port, blockchain)
    api_runner = await start_explorer_api(blockchain, '0.0.0.0', config.port + 100)
    monitor_task = asyncio.create_task(blockchain.peer_monitor())
    
    try:
        await interactive_loop(blockchain, storage, config)
    finally:
        blockchain.running = False
        await monitor_task
        await api_runner.cleanup()
        server.close()
        await server.wait_closed()

if __name__ == '__main__':
    asyncio.run(main())
