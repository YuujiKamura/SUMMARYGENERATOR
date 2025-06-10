import os
import sys
import pytest
# プロジェクトルートとocr_enginesディレクトリをsys.pathに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../app/controllers/ocr_engines')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from app.controllers.ocr_controller import OcrController

# テスト用画像パス
IMAGE_PATH = r"C:\Users\yuuji\Sanyuu2Kouku\cursor_tools\PhotoCategorizer\data\dataset_photos\施工状況\RIMG4755.JPG"

@pytest.mark.timeout(30)
def test_documentai_ocr_real():
    # OcrControllerを初期化
    controller = OcrController()
    # OCR実行
    controller.start_ocr([IMAGE_PATH])
    # OCR結果を取得
    result = controller.ocr_results.get(IMAGE_PATH, None)
    print("OCR結果:", result)
    assert result is not None and result.strip() != "", "OCR結果が空です" 