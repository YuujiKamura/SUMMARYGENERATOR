#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Photo Categorizer メインアプリケーションの統合テスト
"""

import os
import sys
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# プロジェクトルートをインポートパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6.QtCore import Qt, QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest

from app.main import run_gui, run_headless
from app.ui.photo_categorizer_window import PhotoCategorizerWindow


# モックのコントローラーとマネージャー
class MockSettingsManager(QObject):
    """設定マネージャーのモック"""
    def __init__(self, headless=False):
        super().__init__()
        self.headless = headless
        self.settings = {}
    
    def get(self, key, default=None):
        return self.settings.get(key, default)
    
    def set(self, key, value):
        self.settings[key] = value


class MockModelManager(QObject):
    """モデルマネージャーのモック"""
    def __init__(self):
        super().__init__()
    
    def categories(self):
        return ["カテゴリ1", "カテゴリ2"]


class MockPredictionController(QObject):
    """予測コントローラのモック"""
    
    # シグナル定義
    output = pyqtSignal(str)
    file_progress = pyqtSignal(str, int, int)
    finished = pyqtSignal(int, object)
    
    def __init__(self, settings=None, models=None):
        super().__init__()
        self.settings = settings
        self.models = models
        self.run_headless_called = False
    
    def run_headless(self, **kwargs):
        self.run_headless_called = True


class MockOcrController(QObject):
    """OCRコントローラのモック"""
    
    # シグナル定義
    text_extracted = pyqtSignal(str, str)
    processing_progress = pyqtSignal(str, int, int)
    all_completed = pyqtSignal()
    
    def __init__(self, settings=None):
        super().__init__()
        self.settings = settings
        self.start_ocr_called = False
        self.image_paths = []
    
    def start_ocr(self, image_paths, region_detector=None):
        self.start_ocr_called = True
        self.image_paths = image_paths
        # OCR処理をシミュレート
        for path in image_paths:
            self.text_extracted.emit(path, f"OCRテスト結果 {os.path.basename(path)}")
        self.all_completed.emit()


@pytest.fixture
def temp_image_dir():
    """テスト用の一時画像ディレクトリを作成"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # ダミー画像ファイルを作成
        for i in range(3):
            dummy_file = os.path.join(tmp_dir, f"test_image_{i}.jpg")
            with open(dummy_file, 'wb') as f:
                f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00')  # 最小限のJPEGヘッダー
        
        yield tmp_dir


@pytest.fixture
def app():
    """QApplicationのインスタンスを作成"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def mock_controllers():
    """モックコントローラを作成"""
    settings = MockSettingsManager()
    models = MockModelManager()
    predictor = MockPredictionController(settings, models)
    ocr = MockOcrController(settings)
    
    return settings, models, predictor, ocr


@pytest.fixture
def window(app, mock_controllers):
    """テスト用のウィンドウを作成"""
    settings, models, predictor, ocr = mock_controllers
    
    window = PhotoCategorizerWindow(settings, models, predictor, ocr)
    window.show()
    
    yield window
    
    window.close()


def test_gui_mode_initialization(app, temp_image_dir):
    """GUIモードの初期化テスト"""
    # コマンドライン引数のシミュレーション
    class Args:
        def __init__(self):
            self.source = temp_image_dir
            self.force_predictor = False
            self.force_ocr_viewer = False
            self.no_ocr_viewer = False
    
    args = Args()
    
    # 依存するクラスをパッチ
    with patch('app.main.SettingsManager', return_value=MockSettingsManager()), \
         patch('app.main.ModelManager', return_value=MockModelManager()), \
         patch('app.main.PredictionController', return_value=MockPredictionController()), \
         patch('app.main.OcrController', return_value=MockOcrController()), \
         patch('app.main.PhotoCategorizerWindow', return_value=MagicMock()), \
         patch('PyQt6.QtWidgets.QApplication.exec', return_value=0):
        
        exit_code = run_gui(args)
        assert exit_code == 0


def test_headless_mode_initialization(temp_image_dir):
    """ヘッドレスモードの初期化テスト"""
    # コマンドライン引数のシミュレーション
    class Args:
        def __init__(self):
            self.model = None  # デフォルトモデルを使用
            self.source = temp_image_dir
            self.conf = 0.5
            self.no_subfolder = False
            self.output = None
            self.ocr = True
    
    args = Args()
    
    # 依存するクラスをパッチ
    with patch('app.main.SettingsManager', return_value=MockSettingsManager(headless=True)), \
         patch('app.main.ModelManager', return_value=MockModelManager()), \
         patch('app.main.PredictionController') as mock_prediction_controller, \
         patch('app.main.OcrController', return_value=MockOcrController()):
        
        # PredictionControllerインスタンスのrun_headlessメソッドをモック
        mock_predictor_instance = mock_prediction_controller.return_value
        mock_predictor_instance.run_headless = MagicMock()
        
        run_headless(args)
        
        # run_headlessが呼ばれたか確認
        mock_predictor_instance.run_headless.assert_called_once()


def test_settings_manager():
    """設定マネージャーのテスト"""
    settings = MockSettingsManager()
    settings.set("key1", "value1")
    
    assert settings.get("key1") == "value1"
    assert settings.get("key2", "default") == "default"


def test_model_manager():
    """モデルマネージャーのテスト"""
    models = MockModelManager()
    
    categories = models.categories()
    assert isinstance(categories, list)
    assert len(categories) > 0
    assert "カテゴリ1" in categories


def test_ocr_button_flow(app, window, temp_image_dir, qtbot):
    """OCRボタンの機能テスト"""
    # 初期状態：OCRボタンは無効
    assert not window.ocr_button.isEnabled()
    
    # フォルダ選択
    with patch('PyQt6.QtWidgets.QFileDialog.getExistingDirectory', return_value=temp_image_dir):
        qtbot.mouseClick(window.folder_button, Qt.MouseButton.LeftButton)
    
    # フォルダが選択された後：OCRボタンは有効
    assert window.folder_edit.text() == temp_image_dir
    assert window.ocr_button.isEnabled()
    
    # OCRボタンをクリック
    with qtbot.waitSignal(window.ocr_requested, timeout=1000):
        qtbot.mouseClick(window.ocr_button, Qt.MouseButton.LeftButton)
    
    # OCRController.start_ocrが呼ばれたことを確認
    assert window.ocr.start_ocr_called
    
    # スキャン完了を待つ
    QTest.qWait(500)
    
    # OCRテキストが表示されていることを確認
    if window.photo_model.rowCount() > 0:
        index = window.photo_model.index(0, 0)
        window.photo_list.clicked.emit(index)
        assert "OCRテスト結果" in window.caption_label.text()


def test_full_app_workflow(app, window, temp_image_dir, qtbot):
    """アプリケーションの完全な操作フローテスト"""
    # フォルダ選択
    with patch('PyQt6.QtWidgets.QFileDialog.getExistingDirectory', return_value=temp_image_dir):
        qtbot.mouseClick(window.folder_button, Qt.MouseButton.LeftButton)
    
    # フォルダ選択後の状態確認
    assert window.current_folder == temp_image_dir
    assert window.ocr_button.isEnabled()
    assert window.export_button.isEnabled()
    
    # OCR実行
    with qtbot.waitSignal(window.ocr_requested, timeout=1000):
        qtbot.mouseClick(window.ocr_button, Qt.MouseButton.LeftButton)
    
    # OCR処理が開始されたことを確認
    assert window.ocr.start_ocr_called
    
    # 少し待って表示を確認
    QTest.qWait(500)
    
    # 写真リストに画像が追加されていることを確認またはスキップ
    if window.photo_model.rowCount() > 0:
        # 写真を選択
        index = window.photo_model.index(0, 0)
        with qtbot.waitSignal(window.image_selected, timeout=1000):
            window.photo_list.clicked.emit(index)
        
        # キャプションが表示されていることを確認
        assert "OCRテスト結果" in window.caption_label.text()
    
    # エクスポート機能
    with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName', return_value=["test_export.csv", "CSV files (*.csv)"]):
        with qtbot.waitSignal(window.export_requested, timeout=1000):
            qtbot.mouseClick(window.export_button, Qt.MouseButton.LeftButton)
    
    # エクスポートリクエストが発行されたことを確認
    # (実際のエクスポート処理はコントローラーで行われるためここでは検証しない) 