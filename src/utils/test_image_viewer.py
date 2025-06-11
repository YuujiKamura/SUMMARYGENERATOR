#!/usr/bin/env python3
"""
画像ビューワーのテストスクリプト
"""
import sys
import os
from pathlib import Path
import tempfile
import pytest
from PIL import Image
import numpy as np
import logging

# ロガーの設定
logger = logging.getLogger(__name__)

# プロジェクトルートをPython pathに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# テスト用ユーティリティをインポート
from tests.test_utils import setup_qt_test_environment

# PyQt6モジュールをインポート - 明示的にQtをインポート
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, Qt  # Qtを明示的にインポート
from PyQt6.QtTest import QTest

from src.utils.image_viewer import ImageViewerDialog

@pytest.mark.gui
@pytest.mark.unit
def create_test_image(width=640, height=480):
    """テスト用の画像を作成"""
    # 単色の画像を作成
    img = np.ones((height, width, 3), dtype=np.uint8) * 200
    
    # 中央に四角形を描画
    x1, y1 = width // 4, height // 4
    x2, y2 = 3 * width // 4, 3 * height // 4
    img[y1:y2, x1:x2] = [100, 150, 200]
    
    return img

@pytest.mark.gui
@pytest.mark.unit
def test_basic_viewer(monkeypatch):
    """基本的な画像ビューワーの動作テスト"""
    # テスト環境をセットアップ（すでにsetup fixtureで行われている可能性あり）
    setup_qt_test_environment()
    
    # ヘッドレスモードを確実に有効化
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    
    # テスト画像を一時ファイルとして保存
    test_image_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            img = create_test_image()
            Image.fromarray(img).save(tmp.name)
            test_image_path = tmp.name
        
        logger.info(f"テスト画像を作成: {test_image_path}")
        
        # ダミーの検出結果
        test_detections = [
            {
                "class": 0,
                "class_name": "person",
                "confidence": 0.85,
                "xyxy": [100, 100, 300, 200]
            }
        ]
        
        # 既存のQApplicationインスタンスを使用
        app = QApplication.instance()
        assert app is not None, "QApplicationが初期化されていません"
        
        # タイマーで自動終了（テスト用）
        timer = QTimer()
        timer.setSingleShot(True)
        
        try:
            # 画像ビューワーを表示
            logger.info("画像ビューワーを起動中...")
            viewer = ImageViewerDialog(test_image_path, test_detections)
            
            # グロー効果を使わない簡易表示
            logger.info("グロー効果なしで描画")
            viewer.use_glow_effect = False
            
            # ウィンドウの表示（ヘッドレスモードなので実際には表示されない）
            viewer.show()
            
            # アプリケーションイベントを処理
            app.processEvents()
            
            # ウィジェットが有効か確認
            if viewer.toggle_det_btn.isEnabled():
                # 検出情報の表示/非表示切り替え - ボタンをコールに変更
                logger.info("検出情報の表示/非表示を切り替え")
                viewer.toggle_detections()
                assert not viewer.show_detections, "検出情報の表示/非表示切り替えに失敗"
                
                # 再度切り替え
                viewer.toggle_detections()
                assert viewer.show_detections, "検出情報の表示/非表示切り替えに失敗"
            else:
                logger.warning("ボタンが無効のためクリックテストをスキップします")
            
            # タイムアウトで終了
            timer.timeout.connect(viewer.close)
            timer.start(100)  # 0.1秒後に終了
            
            # イベントループを短時間実行
            app.processEvents()
            
            # テスト成功
            logger.info("基本的なビューワーテスト: 成功")
            assert True
            
        except Exception as e:
            logger.error(f"テスト実行中にエラーが発生: {e}", exc_info=True)
            pytest.fail(f"ビューワーテスト失敗: {e}")
            
    finally:
        # テスト画像を削除
        if test_image_path and os.path.exists(test_image_path):
            try:
                os.unlink(test_image_path)
                logger.info(f"テスト画像を削除: {test_image_path}")
            except Exception as e:
                logger.warning(f"テスト画像の削除に失敗: {e}")

@pytest.mark.gui
@pytest.mark.unit
def test_with_glow_effect(monkeypatch):
    """グロー効果付きの画像ビューワーの動作テスト"""
    # テスト環境をセットアップ
    setup_qt_test_environment()
    
    # ヘッドレスモードを確実に有効化
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    
    # テスト画像を一時ファイルとして保存
    test_image_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            img = create_test_image()
            Image.fromarray(img).save(tmp.name)
            test_image_path = tmp.name
        
        logger.info(f"テスト画像を作成: {test_image_path}")
        
        # ダミーの検出結果
        test_detections = [
            {
                "class": 0,
                "class_name": "person",
                "confidence": 0.85,
                "xyxy": [100, 100, 300, 200]
            }
        ]
        
        # 既存のQApplicationインスタンスを使用
        app = QApplication.instance()
        assert app is not None, "QApplicationが初期化されていません"
        
        try:
            # 画像ビューワーを表示
            logger.info("グロー効果ありで画像ビューワーを起動中...")
            viewer = ImageViewerDialog(test_image_path, test_detections)
            
            # グロー効果を有効化
            viewer.use_glow_effect = True
            
            # ウィンドウの表示（ヘッドレスモードなので実際には表示されない）
            viewer.show()
            
            # アプリケーションイベントを処理
            app.processEvents()
            
            # 基本的な操作をテスト - ボタンをコールに変更
            logger.info("検出情報の表示/非表示を切り替え")
            viewer.toggle_detections()
            
            # イベントループを短時間実行
            app.processEvents()
            
            # テスト成功
            logger.info("グロー効果付きビューワーテスト: 成功")
            assert True
            
        except Exception as e:
            logger.error(f"テスト実行中にエラーが発生: {e}", exc_info=True)
            pytest.fail(f"グロー効果テスト失敗: {e}")
            
    finally:
        # テスト画像を削除
        if test_image_path and os.path.exists(test_image_path):
            try:
                os.unlink(test_image_path)
                logger.info(f"テスト画像を削除: {test_image_path}")
            except Exception as e:
                logger.warning(f"テスト画像の削除に失敗: {e}") 