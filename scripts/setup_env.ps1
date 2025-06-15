Param(
    [string]$PythonExe = "python"
)

# PowerShell 用環境セットアップスクリプト
# .\scripts\setup_env.ps1 -PythonExe python3.11  のように実行可能

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

& $PythonExe -m venv .venv
& .\.venv\Scripts\Activate.ps1

& python -m pip install --upgrade pip
& python -m pip install -r requirements.txt

Write-Host "[INFO] Setup complete. Activate with .\.venv\Scripts\Activate.ps1" 