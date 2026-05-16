@echo off
cd /d "%~dp0"
python Quantum.py --network public-testnet --role user --connect-only
pause
