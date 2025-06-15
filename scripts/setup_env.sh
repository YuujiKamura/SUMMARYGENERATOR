#!/usr/bin/env bash
# 環境セットアップスクリプト (Linux/WSL 用)
# 1. Python venv 作成
# 2. pip 最新化
# 3. requirements.txt インストール

set -e

PROJECT_ROOT=$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )
cd "$PROJECT_ROOT"

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "[INFO] Setup complete. Activate with 'source .venv/bin/activate'" 