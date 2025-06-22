#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OCRコントローラーと写真カテゴライザーウィンドウの連携テスト
"""

import os
import sys
import unittest
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# QApplicationのヘッドレスモード設定
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_LOGGING_TO_CONSOLE"] = "0"
os.environ["QT_FORCE_HEADLESS"] = "1"

# Windowsの場合に追加の設定
if sys.platform.startswith('win'):
    os.environ["QT_OPENGL"] = "software"
    os.environ["QT_SCALE_FACTOR"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"

# 現在のディレクトリをモジュール検索パスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Qt.AA_UseSoftwareOpenGLを設定（QApplicationインスタンス作成前に行う必要がある）
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
if sys.platform.startswith('win'):
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL)

from PyQt6.QtCore import QThread, QObject
from PyQt6.QtTest import QTest, QSignalSpy

from app.controllers.settings_manager import SettingsManager
from app.controllers.ocr_controller import OcrController, OcrThread
from app.controllers.dictionary_manager import DictionaryManager
from app.ui.photo_categorizer_window import PhotoCategorizerWindow
from app.utils.paths import OCR_CACHE_FILE


class MockOcrThread(QThread):
    """モックOCRスレッド"""
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.stopped = False
        self.progress = MagicMock()
        self.result = MagicMock()
        self.finished = MagicMock()
    
    def run(self):
        """即時完了するスレッド実装"""
        # テスト用なので実際には何もしない
        pass
    
    def stop(self):
        """停止フラグを設定"""
        self.stopped = True


class TestOcrIntegration(unittest.TestCase):
    """OCR機能の統合テスト"""
    
    @classmethod
    def setUpClass(cls):
        """テストクラスの初期化"""
        # QApplication インスタンスの作成（既に存在する場合は再利用）
        cls.app = QApplication.instance() or QApplication([])
    
    def setUp(self):
        """テストケースの初期化"""
        # 一時ディレクトリの作成
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # 一時キャッシュファイルの準備
        self.temp_cache_file = self.temp_dir / "test_cache.json"
        
        # テスト用画像ファイルのパス
        self.test_images = [
            str(self.temp_dir / "image1.jpg"),
            str(self.temp_dir / "image2.jpg")
        ]
        
        # テスト用画像ファイルを作成
        for img_path in self.test_images:
            with open(img_path, 'w') as f:
                f.write("dummy image content")
        
        # モックデータの準備（実際に存在するパスを使用）
        self.mock_cache_data = {
            self.test_images[0]: "テスト画像1のキャプション",
            self.test_images[1]: "テスト画像2のキャプション"
        }
        
        # キャッシュデータを書き込み
        with open(self.temp_cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.mock_cache_data, f, ensure_ascii=False)
        
        # OCR_CACHE_FILEをパッチ
        self.ocr_cache_patcher = patch('app.utils.paths.OCR_CACHE_FILE', self.temp_cache_file)
        self.ocr_cache_patcher.start()
        
        # OCRスレッドクラスをモック化
        self.thread_patcher = patch('app.controllers.ocr_controller.OcrThread', MockOcrThread)
        self.thread_patcher.start()
        
        # コントローラとウィンドウの準備
        self.settings = SettingsManager()
        self.dictionary = DictionaryManager(self.settings)
        
        # OCRコントローラの作成（強制的に新規インスタンスを作成）
        self.ocr = OcrController(self.settings, self.dictionary)
        self.ocr.cache = self.mock_cache_data.copy()  # キャッシュを直接設定
        
        # 写真カテゴライザーウィンドウの作成
        self.window = PhotoCategorizerWindow(
            self.settings, None, None, self.ocr, self.dictionary
        )
    
    def tearDown(self):
        """テストケース終了時のクリーンアップ"""
        # パッチを停止
        self.thread_patcher.stop()
        self.ocr_cache_patcher.stop()
        
        # ウィンドウのクローズ
        if hasattr(self, 'window'):
            self.window.close()
            
        # 一時ファイルの削除
        if hasattr(self, 'temp_dir') and self.temp_dir.exists():
            import shutil
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                print(f"一時ディレクトリ削除エラー: {e}")
    
    def test_text_extracted_signal_updates_caption(self):
        """OCRテキスト抽出シグナルでキャプションが更新されるかのテスト"""
        # テスト対象の画像パスとキャプション
        test_image_path = self.test_images[0]
        test_caption = "テストキャプション"
        
        # ウィンドウに現在の画像として設定
        self.window.current_image_path = test_image_path
        
        # OCRテキスト抽出シグナルを発行
        self.ocr.text_extracted.emit(test_image_path, test_caption)
        
        # イベントループを処理
        QTest.qWait(100)
        
        # キャプションが更新されたか確認
        self.assertEqual(self.window.image_captions.get(test_image_path), test_caption)
    
    def test_cache_loading_on_startup(self):
        """起動時にキャッシュから正しくロードされるかのテスト"""
        # 一時的なキャッシュファイルを新規作成
        temp_cache = self.temp_dir / "fresh_cache.json"
        fresh_mock_data = {
            "test_path1": "test_caption1",
            "test_path2": "test_caption2"
        }
        
        # キャッシュデータを書き込み
        with open(temp_cache, 'w', encoding='utf-8') as f:
            json.dump(fresh_mock_data, f, ensure_ascii=False)
        
        # 新しいOCRコントローラを作成してキャッシュをロード
        with patch('app.utils.paths.OCR_CACHE_FILE', temp_cache):
            # OCRコントローラのインスタンス作成時に_load_cacheが呼ばれる
            new_ocr = OcrController(self.settings, self.dictionary)
            
            # キャッシュの各エントリを確認
            for key, value in fresh_mock_data.items():
                self.assertIn(key, new_ocr.cache)
                self.assertEqual(new_ocr.cache[key], value)
    
    def test_get_cached_text(self):
        """キャッシュからテキストを取得できるかのテスト"""
        test_image_path = self.test_images[0]
        expected_caption = self.mock_cache_data[test_image_path]
        
        # キャッシュからテキストを取得
        cached_text = self.ocr.get_cached_text(test_image_path)
        
        # 期待するテキストと一致するか確認
        self.assertEqual(cached_text, expected_caption)
    
    def test_set_caption_updates_display(self):
        """set_captionメソッドがキャプション表示を更新するかのテスト"""
        # テスト対象の画像パスとキャプション
        test_image_path = self.test_images[0]
        test_caption = "テストキャプション"
        
        # 現在表示中の画像として設定
        self.window.current_image_path = test_image_path
        
        # キャプション表示更新のスパイ作成
        self.window._display_caption = MagicMock()
        
        # キャプションを設定
        self.window.set_caption(test_image_path, test_caption)
        
        # イベントループを処理
        QTest.qWait(100)
        
        # キャプション表示が更新されたか確認
        self.window._display_caption.assert_called_once_with(test_caption)
        
        # image_captionsに追加されたか確認
        self.assertEqual(self.window.image_captions.get(test_image_path), test_caption)
    
    def test_select_image_displays_caption(self):
        """画像選択時にキャプションが表示されるかのテスト"""
        # テスト画像のパスとキャプション
        test_image_path = self.test_images[0]
        expected_caption = self.mock_cache_data[test_image_path]
        
        # キャプション表示メソッドのモック
        self.window._display_caption = MagicMock()
        
        # 事前にキャプションを設定
        self.window.image_captions[test_image_path] = expected_caption
        
        # ウィンドウの画像選択処理を直接呼び出す
        self.window._on_image_selected(test_image_path)
        
        # イベントループを処理
        QTest.qWait(100)
        
        # 現在の画像パスが更新されたか確認
        self.assertEqual(self.window.current_image_path, test_image_path)
        
        # キャプション表示が呼ばれたか確認
        self.window._display_caption.assert_called_with(expected_caption)
    
    def test_ocr_process_with_cache(self):
        """OCR処理がキャッシュを使用するかのテスト"""
        # テスト画像パスのリスト
        test_images = self.test_images
        
        # text_extractedシグナルをスパイ
        text_extracted_spy = []
        
        # シグナル検出用のハンドラ
        def on_text_extracted(path, text):
            text_extracted_spy.append((path, text))
        
        # シグナルに接続
        self.ocr.text_extracted.connect(on_text_extracted)
        
        try:
            # OCRスレッドのrunメソッドをモック化して即時テキストを返すようにする
            with patch.object(MockOcrThread, 'run', autospec=True) as mock_run:
                # run()を実行したときにOCRの完了シグナルを発行
                def emit_results(*args, **kwargs):
                    thread_self = args[0]  # self引数
                    # 結果シグナルを即時発行（通常はスレッド内で行われる）
                    for img_path in test_images:
                        self.ocr._on_text_extracted(img_path, self.mock_cache_data[img_path])
                    # 終了シグナルを発行
                    thread_self.finished.emit(0)
                
                mock_run.side_effect = emit_results
                
                # OCR処理を開始
                self.ocr.start_ocr(test_images)
                
                # イベントループを処理（シグナルが発火するのを待つ）
                QTest.qWait(200)
                
                # キャッシュからのシグナルが発行されたか確認
                self.assertEqual(len(text_extracted_spy), 2)  # 2つの画像に対してシグナルが発行される
                
                # 発行されたシグナルの内容確認
                for i, (image_path, text) in enumerate(text_extracted_spy):
                    self.assertEqual(image_path, test_images[i])
                    self.assertEqual(text, self.mock_cache_data[image_path])
        finally:
            # シグナル接続を解除
            self.ocr.text_extracted.disconnect(on_text_extracted)


if __name__ == '__main__':
    unittest.main() 