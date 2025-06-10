#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto_annotateモジュールのモック
テスト実行時にsrc.utils.auto_annotateがない場合に使用する
"""
import sys
import logging
from pathlib import Path
import numpy as np

# ロガー設定
logger = logging.getLogger(__name__)

class MockDetector:
    """モックの検出器"""
    def __init__(self, *args, **kwargs):
        self.name = "MockDetector"
    
    def __call__(self, *args, **kwargs):
        return self


def detect_objects_in_image(image_path, prompt, *args, **kwargs):
    """画像内のオブジェクトを検出するモック関数"""
    logger.info(f"モック検出: {image_path}, プロンプト: {prompt}")
    # 検出結果を返す
    return [
        {
            "bbox": [100, 100, 300, 300],  # x1, y1, x2, y2
            "score": 0.85,
            "label": prompt.split()[0]  # プロンプトの最初の単語をラベルとして使用
        }
    ]


def _init_grounding_dino_sam(*args, **kwargs):
    """Grounding DINO + SAMモデルを初期化するモック関数"""
    logger.info("モックモデルを初期化")
    return MockDetector()


# モジュールとして実行された場合に情報を表示
if __name__ == "__main__":
    print("これはauto_annotateモジュールのモックです。")
    print("テスト実行時にインポートされることを想定しています。") 