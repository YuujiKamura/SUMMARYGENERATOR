from __future__ import annotations

"""ocr_detection_action.py
OCR測点検出アクションを独立モジュールとして提供する。
`run_ocr_detection(parent)` を呼び出すと、現在ロード済みの画像リストに
対して CaptionBoard OCR を実行し、取得した SurveyPoint を DB(images)
テーブルへ登録または更新する。
"""

import os
import datetime
from typing import Any

from PyQt6.QtWidgets import QMessageBox

# --- OCR パイプライン --------------------------------------------------
from ocr_tools.process_caption_board_ocr import CaptionBoardOCRPipeline
from src.utils.image_entry import ImageEntry
from src.db_manager import DBConnection


def run_ocr_detection(parent: Any):
    """編集メニューなどから呼び出すエントリポイント"""
    try:
        entries = getattr(parent, "entries", None)
        if not entries:
            QMessageBox.information(parent, "情報", "画像リストが読み込まれていません。")
            return

        # プロジェクトルート・src_dir を解決
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        src_dir = os.path.join(project_root, "src")
        pipeline = CaptionBoardOCRPipeline(project_root, src_dir)
        if not pipeline.initialize_engine():
            QMessageBox.warning(parent, "エラー", "OCRエンジンの初期化に失敗しました。")
            return

        # OCR 実行 ------------------------------------------------------
        image_entries = []
        for ent in entries:
            img_entry = ent if isinstance(ent, ImageEntry) else ImageEntry(image_path=getattr(ent, "image_path", None))
            pipeline.process_image_entry(img_entry)
            image_entries.append(img_entry)

        # DB登録 --------------------------------------------------------
        with DBConnection() as conn:
            for e in image_entries:
                if not e.survey_point:
                    continue
                sp = e.survey_point
                taken_at = None
                if sp.capture_time:
                    taken_at = datetime.datetime.fromtimestamp(sp.capture_time).strftime('%Y-%m-%d %H:%M:%S')
                location_val = sp.get("location") if hasattr(sp, "get") else None

                cur = conn.execute("SELECT id FROM images WHERE image_path = ?", (e.image_path,))
                row = cur.fetchone()
                if row:
                    conn.execute(
                        "UPDATE images SET location = ?, taken_at = ? WHERE id = ?",
                        (location_val, taken_at, row[0]),
                    )
                    img_id = row[0]
                else:
                    conn.execute(
                        "INSERT INTO images (filename, image_path, taken_at, location) VALUES (?, ?, ?, ?)",
                        (os.path.basename(e.image_path), e.image_path, taken_at, location_val),
                    )
                    img_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

                # --- 個別画像キャッシュJSONへ location を反映 ---
                try:
                    cache_path = e.get_cache_json_path()
                    if cache_path:
                        import json
                        from pathlib import Path
                        Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
                        data = {}
                        if os.path.exists(cache_path):
                            with open(cache_path, "r", encoding="utf-8") as f:
                                try:
                                    data = json.load(f)
                                except json.JSONDecodeError:
                                    data = {}
                        # SurveyPoint 全体を保存（location, date, count, capture_time など）
                        sp_dict = sp.to_dict() if hasattr(sp, "to_dict") else {}
                        data["survey_point"] = sp_dict
                        # 後方互換: location をトップレベルにも保持
                        if location_val is not None:
                            data["location"] = location_val
                        # capture_time もトップレベルに保持
                        if sp.capture_time is not None:
                            data["capture_time"] = sp.capture_time
                        with open(cache_path, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                except Exception as cache_e:
                    print(f"[CACHE_UPDATE_ERROR] {cache_e}")

                # --- survey_points テーブル更新 ---
                try:
                    from src.db_manager import SurveyPointManager
                    SurveyPointManager.upsert_survey_point(img_id, sp.to_dict())
                except Exception as sp_e:
                    print(f"[SurveyPointDB_ERROR] {sp_e}")

            conn.commit()

        QMessageBox.information(parent, "完了", "OCR測点検出が終了し、データベースへ登録しました。")

    except Exception as exc:
        QMessageBox.critical(parent, "エラー", f"OCR検出処理でエラー: {exc}") 