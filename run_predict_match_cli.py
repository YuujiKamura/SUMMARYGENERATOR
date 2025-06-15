#!/usr/bin/env python3
# flake8: noqa
"""Run Predict+Match CLI

画像フォルダを入力として
1) YOLOv8 推論
2) ChainRecord マッチング
3) Excel フォトブック & JSON 出力
を実行する簡易 CLI。

処理ロジックは src.services.predict_match_service.PredictMatchService に委譲し、
このランナーは引数解釈とロギング設定のみを担当する。
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# プロジェクト src を import パスに追加
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# --- ロギング設定 -------------------------------------------------------------
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)
fmt = "[%(asctime)s][%(levelname)s] %(message)s"
for h in LOGGER.handlers[:]:
    LOGGER.removeHandler(h)
logging.basicConfig(level=logging.INFO, format=fmt)

# --- 引数 ---------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="YOLO 推論→辞書マッチ→Excel 出力 CLI")
    p.add_argument("image_dir", type=str, help="入力画像フォルダ")
    p.add_argument("--conf", type=float, default=0.10, help="信頼度閾値")
    p.add_argument("--out", type=str, default="prediction_match_results.xlsx", help="出力 Excel ファイル")
    p.add_argument("--json-out", type=str, default="prediction_match_results.json", help="中間 JSON 出力")
    return p.parse_args()

# --- メイン -------------------------------------------------------------------


def main() -> None:
    args = parse_args()
    image_dir = Path(args.image_dir).expanduser().resolve()
    if not image_dir.exists() or not image_dir.is_dir():
        LOGGER.error("画像ディレクトリが見つかりません: %s", image_dir)
        sys.exit(1)

    out_excel = Path(args.out).expanduser().resolve()
    out_json = Path(args.json_out).expanduser().resolve()

    from src.services.predict_match_service import PredictMatchService

    svc = PredictMatchService()
    svc.process(
        image_dir=image_dir,
        conf=args.conf,
        out_excel=out_excel,
        out_json=out_json,
    )

    LOGGER.info("処理完了")


if __name__ == "__main__":
    main() 