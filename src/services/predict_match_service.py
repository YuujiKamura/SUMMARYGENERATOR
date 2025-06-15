#!/usr/bin/env python3
"""predict_match_service

YOLO 推論 → ChainRecord マッチング → Excel フォトブック出力
を 1 つのサービスクラスにまとめるユーティリティ。

CLI や GUI から呼び出せる共通処理として切り出した。
"""

from __future__ import annotations

import logging
from pathlib import Path
import os

from src.utils.path_manager import PathManager
from src.utils.csv_records_loader import load_records_and_roles_csv
from src.utils.excel_photobook_exporter import export_excel_photobook
from src.new_matcher import match_images_with_chain_records
from src.utils.match_results_serializer import to_dict_list, save_json
from src.utils.yolo_detection_utils import split_roles_bboxes, detect_dir
from src.utils.model_finder import find_latest_best_model
from src import db_manager  # dynamic DB path override

LOGGER = logging.getLogger(__name__)

class PredictMatchService:
    """画像フォルダに対する推論・マッチ・エクスポート一括サービス"""

    def __init__(self, *, path_manager: PathManager | None = None):
        self.pm = path_manager or PathManager()
        # --- 独立DBを初期化 ---
        self.db_path = self.pm.project_root / "predict_match.db"
        # 既存ファイルは毎回リセット（混在防止）
        try:
            self.db_path.unlink(missing_ok=True)  # Python 3.8+
        except TypeError:
            # 古いPythonではmissing_ok未対応
            if self.db_path.exists():
                self.db_path.unlink()
        db_manager.DB_PATH = self.db_path  # override global path in module
        db_manager.init_db(self.db_path)

    # ---------------------------------------------------------------------
    # パイプライン
    # ---------------------------------------------------------------------
    def process(
        self,
        image_dir: Path,
        *,
        conf: float = 0.10,
        recursive: bool = True,
        out_excel: Path,
        out_json: Path | None = None,
        location: str | None = None,
    ) -> None:
        """ディレクトリを受け取りフォトブックと JSON を出力"""
        # 1. モデル取得
        model_path = find_latest_best_model(self.pm.model_search_dirs)
        LOGGER.info("使用モデル: %s", model_path)

        # 2. 推論
        det_results = detect_dir(image_dir, str(model_path), conf=conf, recursive=recursive)

        # 2.5 画像をDBへ登録（重複は無視）
        for img_path in det_results.keys():
            try:
                db_manager.ImageManager.add_image(os.path.basename(img_path), img_path, location=location)
            except Exception:
                pass  # UNIQUE 制約などはスキップ

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