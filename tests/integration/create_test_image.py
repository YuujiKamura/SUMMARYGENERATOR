#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
テスト用ダミー画像を作成するスクリプト
"""
import os
import sys
import cv2
import numpy as np
from pathlib import Path

# プロジェクトのルートディレクトリをシステムパスに追加
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

def create_test_images():
    """テスト用の画像を作成する"""
    # テスト画像ディレクトリの作成
    test_images_dir = ROOT / "test_images"
    test_images_dir.mkdir(exist_ok=True, parents=True)
    
    # サンプル画像の作成
    for name in ["board_sample.jpg", "test_board.jpg", "sample.jpg"]:
        img_path = test_images_dir / name
        if not img_path.exists():
            print(f"画像を作成: {img_path}")
            # ダミー画像の生成（白背景に黒い四角）
            img = np.ones((480, 640, 3), dtype=np.uint8) * 255
            # 中央に黒い四角を描画（疑似的な管理図ボード）
            cv2.rectangle(img, (160, 120), (480, 360), (0, 0, 0), -1)
            # ボードらしく見せるための内部グリッド
            for i in range(180, 460, 40):
                cv2.line(img, (180, i), (460, i), (255, 255, 255), 1)
            for i in range(200, 440, 40):
                cv2.line(img, (i, 140), (i, 340), (255, 255, 255), 1)
            # 画像の保存
            cv2.imwrite(str(img_path), img)
        else:
            print(f"画像が既に存在: {img_path}")

if __name__ == "__main__":
    create_test_images()
    print("テスト画像の作成が完了しました。") 