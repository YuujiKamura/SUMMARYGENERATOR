import pytest
from src.utils.records_loader import load_records_from_json, save_records_to_json
import os
import json
import tempfile

def test_load_and_save_records():
    # テスト用の一時ファイルを作成
    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = os.path.join(tmpdir, "test.json")
        # サンプルデータ（従来型）
        records = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"}
        ]
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({"records": records}, f, ensure_ascii=False, indent=2)
        # 読み込みテスト
        loaded = load_records_from_json(json_path)
        assert loaded == records
        # 保存テスト
        new_records = [
            {"id": 3, "name": "Carol"},
            {"id": 4, "name": "Dave"}
        ]
        save_records_to_json(json_path, new_records, as_reference=False)
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["records"] == new_records
