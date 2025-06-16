import os
import sys

# summarygeneratorプロジェクト用のパス設定
current_dir = os.path.dirname(os.path.abspath(__file__))
ocr_tools_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(ocr_tools_dir)
src_dir = os.path.join(project_root, 'src')

# パスを追加
sys.path.insert(0, ocr_tools_dir)
sys.path.insert(0, src_dir)

from ocr_value_pair_detector import detect_value_pairs_from_boxes
from ocr_aa_layout import print_ocr_aa_layout
import json

def test_detect_arrival_temperature_pair():
    data_path = os.path.join(os.path.dirname(__file__), "data", "ocr_sample_texts_with_boxes.json")
    with open(data_path, encoding="utf-8") as f:
        texts_with_boxes = json.load(f)
    pairs = detect_value_pairs_from_boxes(texts_with_boxes, keyword_list=["到着温度"])
    assert any(p["keyword"] == "到着温度" and abs(p["value"] - 159.6) < 0.01 for p in pairs)
    # AAレイアウトでキーワード・値側両方にマーク
    highlight_boxes = [p["keyword_box"] for p in pairs] + [p["value_box"] for p in pairs]
    print("\n--- AAレイアウト ---")
    print_ocr_aa_layout(texts_with_boxes, image_width=1280, image_height=960, highlight_boxes=highlight_boxes)

if __name__ == "__main__":
    test_detect_arrival_temperature_pair()
    print("OK")