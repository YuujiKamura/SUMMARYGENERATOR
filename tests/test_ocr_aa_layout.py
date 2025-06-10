import sys
import os
import io
import json
from contextlib import redirect_stdout
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from ocr_aa_layout import print_ocr_aa_layout

def main():
    test_aa_layout_from_texts_with_boxes()

def test_aa_layout_from_texts_with_boxes():
    # texts_with_boxesをロード
    with open('tests/data/ocr_sample_texts_with_boxes.json', encoding='utf-8') as f:
        texts_with_boxes = json.load(f)

    # print出力をキャプチャ
    buf = io.StringIO()
    with redirect_stdout(buf):
        print_ocr_aa_layout(texts_with_boxes, image_width=1280, image_height=960)
    actual_aa = buf.getvalue().strip()

    print("--- actual_aa ---")
    print(actual_aa)

if __name__ == '__main__':
    main() 