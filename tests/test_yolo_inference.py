# tests/test_yolo_inference.py
import os
from pathlib import Path

import pytest
from ultralytics import YOLO
import torch

# プロジェクトルート
ROOT = Path(__file__).parent.parent.resolve()
MODEL_PATH = ROOT / "yolo" / "yolov8n.pt"
TEST_IMAGE = ROOT / "tests" / "data" / "test_image.jpg"

@pytest.fixture(autouse=True)
def check_files_exist():
    assert MODEL_PATH.exists(), f"モデルが見つかりません: {MODEL_PATH}"
    assert TEST_IMAGE.exists(), f"画像が見つかりません: {TEST_IMAGE}"
    yield

@pytest.mark.yolo
@pytest.mark.inference
def test_whitelist_inference():
    """ホワイトリスト方式でモデルがロード→推論できる"""
    model = YOLO(str(MODEL_PATH))
    results = model.predict(str(TEST_IMAGE))
    assert isinstance(results, list)
    assert len(results) >= 1
    first = results[0]
    assert hasattr(first, "boxes")
    # 検出ボックス数が 0以上
    assert first.boxes.shape[0] >= 0

@pytest.mark.yolo
@pytest.mark.inference
def test_monkeypatch_inference(monkeypatch):
    """monkeypatch で torch.load を差し替えても推論が通る"""
    orig = torch.load
    def patched_load(f, **kw):
        kw.setdefault("weights_only", False)
        return orig(f, **kw)
    monkeypatch.setattr(torch, "load", patched_load)

    model = YOLO(str(MODEL_PATH))
    results = model.predict(str(TEST_IMAGE))
    assert isinstance(results, list)
    assert len(results) >= 1
    first = results[0]
    assert hasattr(first, "boxes")
