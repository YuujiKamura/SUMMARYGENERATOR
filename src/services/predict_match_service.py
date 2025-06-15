#!/usr/bin/env python3
"""predict_match_service

YOLO 推論 → ChainRecord マッチング → Excel フォトブック出力
を 1 つのサービスクラスにまとめるユーティリティ。

CLI や GUI から呼び出せる共通処理として切り出した。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.utils.yolo_predict_cli import detect_boxes_with_yolo

from src.utils.path_manager import PathManager
from src.utils.csv_records_loader import load_records_and_roles_csv
from src.utils.excel_photobook_exporter import export_excel_photobook
from src.new_matcher import match_images_with_chain_records
from src.utils.match_results_serializer import to_dict_list, save_json
from src.utils.yolo_detection_utils import split_roles_bboxes, detect_dir
from src.utils.model_finder import find_latest_best_model

LOGGER = logging.getLogger(__name__)


class PredictMatchService:
    """画像フォルダに対する推論・マッチ・エクスポート一括サービス"""

    def __init__(self, *, path_manager: PathManager | None = None):
        self.pm = path_manager or PathManager()

    # ---------------------------------------------------------------------
    # マッチング
    # ---------------------------------------------------------------------
    # match_records メソッドは役割を終えたため削除しました。

    # ---------------------------------------------------------------------
    # パイプライン
    # ---------------------------------------------------------------------
    def process(
        self,
        image_dir: Path,
        *,
        conf: float = 0.10,
        out_excel: Path,
        out_json: Path | None = None,
    ) -> None:
        """ディレクトリを受け取りフォトブックと JSON を出力"""
        # 1. モデル取得
        model_path = find_latest_best_model(self.pm.model_search_dirs)
        LOGGER.info("使用モデル: %s", model_path)

        # 2. 推論
        det_results = detect_dir(image_dir, str(model_path), conf=conf)

        # 3. CSV 取得
        csv_path = self.pm.records_and_roles_csv
        records, role_mapping = load_records_and_roles_csv(csv_path)
        LOGGER.info("CSV 読込: records=%d mappings=%d", len(records), len(role_mapping))

        # det_results → image_roles / image_bboxes へ整形
        image_roles, image_bboxes = split_roles_bboxes(det_results)

        # 4. マッチング (util 1 行)
        images = [{"image_path": p, "bboxes": b} for p, b in image_bboxes.items()]
        match_results = match_images_with_chain_records(images, role_mapping, records)
        json_items = to_dict_list(match_results, image_roles=image_roles, image_bboxes=image_bboxes)

        # 5. Excel フォトブック出力
        cache_dir = self.pm.src_dir / "image_preview_cache"
        export_excel_photobook(
            match_results,
            {},
            records,
            str(out_excel),
            cache_dir=str(cache_dir),
        )
        LOGGER.info("Excel 出力完了: %s", out_excel)

        # 6. JSON 保存
        if out_json:
            save_json(match_results, out_json, image_roles=image_roles, image_bboxes=image_bboxes)
            LOGGER.info("JSON 出力完了: %s", out_json) 