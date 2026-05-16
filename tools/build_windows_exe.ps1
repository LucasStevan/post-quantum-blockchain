Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m pip install pyinstaller==6.17.0
.\.venv\Scripts\python -m PyInstaller packaging\QuantumNode.spec

Write-Host "Built dist\QuantumNode.exe"
