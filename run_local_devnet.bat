@echo off
cd /d "%~dp0"
python Quantum.py --network local-devnet --role user
pause
