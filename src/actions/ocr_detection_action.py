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
from src.db_manager import DBConnection, init_db, ensure_images_columns


def run_ocr_detection(parent: Any):
    """編集メニューなどから呼び出すエントリポイント"""
    try:
        init_db()
        ensure_images_columns()

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
        from src.utils.image_entry import ImageEntryList
        from ocr_tools.supplement_runner import SupplementRunner, TIME_WINDOW_SEC as _TW

        image_entries = []
        for ent in entries:
            img_entry = ent if isinstance(ent, ImageEntry) else ImageEntry(image_path=getattr(ent, "image_path", None))
            pipeline.process_image_entry(img_entry)
            image_entries.append(img_entry)

        # 補完ロジックを適用して最終結果を取得
        image_entry_list = ImageEntryList(entries=image_entries, group_type="ui_images")
        final_results = SupplementRunner.run(image_entry_list, _TW)

        # DB登録 --------------------------------------------------------
        with DBConnection() as conn:
            conn.execute("BEGIN")
            for res in final_results:
                img_path = res.get("image_path")
                if not img_path:
                    continue

                # 値取得
                location_val = res.get("location_value") or res.get("inferred_location")
                date_val = res.get("date_value")
                count_val = res.get("count_value")
                capture_time = res.get("capture_time")

                taken_at = None
                if capture_time:
                    taken_at = datetime.datetime.fromtimestamp(capture_time).strftime('%Y-%m-%d %H:%M:%S')

                cur = conn.execute("SELECT id FROM images WHERE image_path = ?", (img_path,))
                row = cur.fetchone()
                if row:
                    img_id = row[0]
                    conn.execute("UPDATE images SET location = ?, taken_at = ? WHERE id = ?",
                                 (location_val, taken_at, img_id))
                else:
                    conn.execute("INSERT INTO images (filename, image_path, taken_at, location) VALUES (?, ?, ?, ?)",
                                 (os.path.basename(img_path), img_path, taken_at, location_val))
                    img_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

                # survey_points upsert
                from src.db_manager import SurveyPointManager
                SurveyPointManager.upsert_survey_point(img_id, res, conn)

                # --- 個別画像キャッシュJSON更新 ----------------------
                try:
                    from src.utils.image_entry import ImageEntry
                    tmp_entry = ImageEntry(image_path=img_path)
                    cache_path = tmp_entry.get_cache_json_path()
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
                        data["survey_point"] = res
                        if location_val is not None:
                            data["location"] = location_val
                        if capture_time is not None:
                            data["capture_time"] = capture_time
                        with open(cache_path, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                except Exception as cache_e:
                    print(f"[CACHE_UPDATE_ERROR] {cache_e}")

            conn.commit()

        QMessageBox.information(parent, "完了", "OCR測点検出が終了し、データベースへ登録しました。")

    except Exception as exc:
        QMessageBox.critical(parent, "エラー", f"OCR検出処理でエラー: {exc}") 