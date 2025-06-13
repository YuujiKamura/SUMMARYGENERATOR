# 旧 summary_generator.py のmain関数のみ退避
import glob
import os
import json
from src.utils.role_mapping_utils import load_role_mapping
from src.utils.records_loader import load_records_from_json
from src.utils.path_manager import path_manager
from src.utils.image_data_manager import ImageDataManager
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from pathlib import Path

RECORDS_PATH = str(path_manager.default_records)
OUTPUT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../output/summary_highres.xlsx'))
CACHE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../image_preview_cache'))
IMG_WIDTH = 1280
IMG_HEIGHT = 960

def main():
    mapping = load_role_mapping()
    # --- 旧: image_json_dict = ... ファイル直集計 ---
    # 新: DB経由で画像リスト・情報を取得
    image_data_manager = ImageDataManager.from_db()
    image_json_dict = {entry.image_path: entry for entry in image_data_manager.entries}
    records = load_records_from_json(RECORDS_PATH)
    # ここで必要ならexport_highres_summary等を呼び出す
    print(f"[INFO] DBから画像{len(image_json_dict)}件を取得 (image_json_dict) に格納")
    print("[INFO] 旧main関数の処理がここに来ます")

if __name__ == "__main__":
    main()

# [移行メモ]
# このスクリプトは「旧: image_preview_cache/*.json 直集計」→「新: ImageDataManager.from_db()でDB経由取得」への移行例です。
# 他に同様のキャッシュ直集計箇所があれば、同じくImageDataManager.from_db()等で置き換えてください。
# 依存箇所は現状このファイルのみ（grep済み）。
# テストや他スクリプトで使う場合は、同様の移行が必要です。
