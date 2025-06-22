import json
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from ocr_value_pair_detector import detect_value_pairs_from_boxes
from ocr_aa_layout import print_ocr_aa_layout

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