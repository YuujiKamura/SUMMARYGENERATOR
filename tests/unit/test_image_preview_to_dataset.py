import os
import tempfile
import json
from pathlib import Path
import pytest
from src.scan_for_images_dataset import image_preview_json_to_dataset_entry
from src.yolo_dataset_exporter import YoloDatasetExporter
from PIL import Image

def make_test_image(image_path):
    img = Image.new("RGB", (32, 32), (255, 255, 255))
    img.save(image_path)

def test_image_preview_json_to_dataset_and_yolo():
    with tempfile.TemporaryDirectory() as tmpdir:
        # テスト用image_preview_cache JSONを作成
        cache_dir = Path(tmpdir) / "image_preview_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        image_dir = Path(tmpdir) / "images"
        image_dir.mkdir(parents=True, exist_ok=True)
        img_path = image_dir / "test_img.jpg"
        make_test_image(img_path)
        # bboxは画像内に収まる値
        test_json = {
            "image_path": str(img_path),
            "bboxes": [
                {"role": "notice_sign_board", "bbox": [1, 2, 30, 20]}
            ]
        }
        json_path = cache_dir / "test.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(test_json, f, ensure_ascii=False, indent=2)
        # 変換
        entry = image_preview_json_to_dataset_entry(str(json_path))
        assert entry["image_path"] == str(img_path)
        assert entry["bboxes"][0]["role"] == "notice_sign_board"
        # DataSet型1件でYOLOエクスポート
        scan_json_path = Path(tmpdir) / "scan_for_images_dataset.json"
        with open(scan_json_path, "w", encoding="utf-8") as f:
            json.dump([entry], f, ensure_ascii=False, indent=2)
        exporter = YoloDatasetExporter([str(scan_json_path)], val_ratio=0.0)
        result = exporter.export(force_flush=True)
        label_dir_train = Path(result["output_dir"]) / "labels" / "train"
        label_files = list(label_dir_train.glob("*.txt"))
        assert label_files, "ラベルファイルが出力されていない"
        with open(label_files[0], "r", encoding="utf-8") as f:
            label_content = f.read()
        assert label_content.startswith("0 "), f"ラベルファイルの内容不正: {label_content}" 