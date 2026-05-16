import os
import subprocess
import sys


ROOT = os.path.dirname(os.path.abspath(__file__))


def choose(prompt, choices, default):
    print(prompt)
    for key, label in choices:
        print(f"{key}. {label}")
    answer = input(f"> [{default}] ").strip() or default
    return answer


def main():
    os.chdir(ROOT)
    print("PQC-CHAIN Launcher")
    print("==================")
    print("Normal users do not need to open router ports. The wallet runs outbound-only and discovers bootnodes.")
    print()

    mode = choose(
        "Choose how to start:",
        [
            ("1", "Public testnet wallet/node (outbound-only)"),
            ("2", "Local devnet node (for your machine/LAN)"),
            ("3", "Public bootnode/archive node (operator mode)"),
        ],
        "1",
    )

    if mode == "1":
        args = ["Quantum.py", "--network", "public-testnet", "--role", "user", "--connect-only"]
    elif mode == "2":
        args = ["Quantum.py", "--network", "local-devnet", "--role", "user"]
    elif mode == "3":
        public_host = input("Public DNS name for this bootnode (example: seed1.yourdomain.com): ").strip()
        if not public_host:
            raise SystemExit("A public DNS name is required for bootnode mode.")
        args = ["Quantum.py", "--network", "bootnode", "--role", "bootnode", "--public-host", public_host, "--no-wallet"]
    else:
        raise SystemExit("Invalid option.")

    raise SystemExit(subprocess.call([sys.executable, *args]))


if __name__ == "__main__":
    main()
