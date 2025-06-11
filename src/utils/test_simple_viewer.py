#!/usr/bin/env python3
"""
シンプルな画像ビューワーのテスト
"""
import sys
import os
from pathlib import Path
import tempfile
from PIL import Image
import numpy as np

# プロジェクトルートをPython pathに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 標準の画像ビューワーの代わりにシンプル版を使用
from src.utils.image_viewer_simple import SimpleImageViewerDialog
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

def create_test_image(width=640, height=480):
    """テスト用の画像を作成"""
    # 単色の画像を作成
    img = np.ones((height, width, 3), dtype=np.uint8) * 200
    
    # 中央に四角形を描画
    x1, y1 = width // 4, height // 4
    x2, y2 = 3 * width // 4, 3 * height // 4
    img[y1:y2, x1:x2] = [100, 150, 200]
    
    return img

def test_simple_viewer():
    """シンプルな画像ビューワーのテスト"""
    print("シンプルな画像ビューワーのテストを開始します...")
    
    # テスト画像を作成して一時ファイルとして保存
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        img = create_test_image()
        Image.fromarray(img).save(tmp.name)
        test_image_path = tmp.name
    
    print(f"テスト画像を作成しました: {test_image_path}")
    
    # ダミーの検出結果
    test_detections = [
        {
            "class": 0,
            "class_name": "テスト",
            "confidence": 0.85,
            "xyxy": [100, 100, 300, 200]
        }
    ]
    
    # QApplicationインスタンスを作成
    app = QApplication(sys.argv)
    
    # タイマーで自動終了（テスト用）
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(app.quit)
    
    try:
        print("ビューワーを起動しています...")
        viewer = SimpleImageViewerDialog(test_image_path, test_detections)
        viewer.show()
        
        # 3秒後に自動終了
        timer.start(3000)
        
        print("テスト中...")
        app.exec()
        print("テスト完了: 正常に終了しました")
        return True
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return False
    finally:
        # テスト画像を削除
        try:
            os.unlink(test_image_path)
            print(f"テスト画像を削除しました: {test_image_path}")
        except:
            pass

def test_with_real_image():
    """実際の画像ファイルを使ったテスト"""
    # 既存の画像ファイルを探す
    for test_dir in ['yolo/images', 'runs/predict/simple_predict', '.']:
        image_files = list(Path(test_dir).glob('*.jpg')) + list(Path(test_dir).glob('*.png'))
        if image_files:
            test_image = str(image_files[0])
            break
    else:
        print("テスト用の画像ファイルが見つかりませんでした")
        return False
    
    print(f"既存の画像ファイルを使用: {test_image}")
    
    # ダミーの検出結果
    test_detections = [
        {
            "class": 0,
            "class_name": "テスト",
            "confidence": 0.85,
            "xyxy": [100, 100, 300, 200]
        }
    ]
    
    # QApplicationインスタンスを作成
    app = QApplication(sys.argv)
    
    # タイマーで自動終了（テスト用）
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(app.quit)
    
    try:
        print("実際の画像でビューワーを起動しています...")
        viewer = SimpleImageViewerDialog(test_image, test_detections)
        viewer.show()
        
        # 3秒後に自動終了
        timer.start(3000)
        
        print("テスト中...")
        app.exec()
        print("実際の画像でのテスト完了: 正常に終了しました")
        return True
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return False

if __name__ == "__main__":
    print("=== シンプルな画像ビューワーのテスト開始 ===")
    
    # 生成した画像でテスト
    synthetic_test_result = test_simple_viewer()
    
    # 実際の画像でテスト
    if synthetic_test_result:
        real_image_test_result = test_with_real_image()
    else:
        real_image_test_result = False
    
    # 結果を表示
    print("\n=== テスト結果 ===")
    print(f"生成画像でのテスト: {'成功' if synthetic_test_result else '失敗'}")
    print(f"実際の画像でのテスト: {'成功' if real_image_test_result else '失敗'}")
    
    # 成功か失敗かの終了コードを返す
    sys.exit(0 if synthetic_test_result and real_image_test_result else 1) 