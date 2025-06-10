#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pytestの設定ファイル
"""
import os
import sys
import pytest
import logging
from pathlib import Path
import tempfile
from unittest.mock import patch
from PyQt6.QtWidgets import QMessageBox, QApplication
from PyQt6.QtCore import QObject, pyqtSignal
import warnings

# test_utilsからの関数をインラインで定義
def setup_qt_test_environment():
    """Qtテスト環境をセットアップ"""
    # ヘッドレスモードを設定
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["QT_LOGGING_TO_CONSOLE"] = "0"
    os.environ["QT_FORCE_HEADLESS"] = "1"
    
    # QApplicationが存在しない場合のみ作成
    if not QApplication.instance():
        try:
            app = QApplication(sys.argv)
            return True
        except Exception as e:
            print(f"Qt環境のセットアップに失敗: {e}")
            return False
    return True

# ルートディレクトリをPythonパスに追加
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# GUI表示を完全に無効化する設定（最初に実行）
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_LOGGING_TO_CONSOLE"] = "0"
os.environ["QT_FORCE_HEADLESS"] = "1"

# ロガーの設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# コンソールにログを出力するハンドラを追加
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# 警告抑制を最初から有効化
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# QApplicationインスタンスの作成（必要な場合）
if not QApplication.instance():
    app = QApplication(sys.argv)
    logger.info("QApplication instance created")

def pytest_configure(config):
    """テスト実行前の設定"""
    # カスタムマーカーの登録（pytest.iniに定義済みだが、念のため登録）
    config.addinivalue_line("markers", "unit: モック中心の高速なユニットテスト")
    config.addinivalue_line("markers", "smoke: 実際のモデルを使用する統合テスト")
    config.addinivalue_line("markers", "schema: JSONデータ構造を検証するスキーマテスト")

    # テストマネージャGUIでの実行時に追加の設定
    if 'PYTEST_CURRENT_TEST' in os.environ:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        os.environ["PYTHONWARNINGS"] = "ignore"


@pytest.fixture(scope="session")
def root_dir():
    """プロジェクトのルートディレクトリを返すフィクスチャ"""
    return ROOT


@pytest.fixture(scope="session")
def test_data_dir(root_dir):
    """テストデータディレクトリを返すフィクスチャ"""
    test_data = root_dir / "tests" / "test_data"
    test_data.mkdir(exist_ok=True, parents=True)
    return test_data


@pytest.fixture(autouse=True)
def cleanup_after_test():
    """各テスト実行後にクリーンアップを行うフィクスチャ"""
    # テスト実行前の処理
    yield
    # テスト実行後の処理
    # メモリリークを防ぐためのクリーンアップなど
    import gc
    gc.collect()


# ===== 共通フィクスチャ =====

@pytest.fixture(scope="session")
def temp_settings_dir():
    """テスト用の一時設定ディレクトリを作成"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # キャッシュフォルダが必要な場合は作成
        data_dir = Path(temp_dir) / "data"
        data_dir.mkdir(exist_ok=True)
        yield temp_dir


@pytest.fixture
def settings_path(temp_settings_dir):
    """設定ファイルパスを取得"""
    return os.path.join(temp_settings_dir, "test_settings.ini")


@pytest.fixture
def patched_settings(settings_path):
    """設定ファイルパスをパッチ"""
    with patch('src.yolo_predict_app.get_settings_path', return_value=settings_path):
        yield


@pytest.fixture
def patched_file_dialog():
    """ファイル選択ダイアログをパッチ"""
    with patch('PyQt6.QtWidgets.QFileDialog.getExistingDirectory', return_value="/test/images/dir"):
        yield


@pytest.fixture
def patched_msg_box():
    """メッセージボックスをパッチ"""
    with patch('PyQt6.QtWidgets.QMessageBox.question', 
               return_value=QMessageBox.StandardButton.Yes) as mock:
        yield mock


@pytest.fixture
def patched_path_exists():
    """ファイル存在チェックをパッチ"""
    with patch('os.path.exists', return_value=True):
        yield 

# QApplicationを全テストで共有するフィクスチャ
@pytest.fixture(scope="session")
def qapp():
    """全テストで共有するQApplicationインスタンスを提供"""
    try:
        # 既存のインスタンスがあれば再利用
        app = QApplication.instance()
        if app is None:
            # ヘッドレスモードの再確認
            os.environ["QT_QPA_PLATFORM"] = "offscreen"
            # 新しいインスタンスを作成
            app = QApplication(["-platform", "offscreen"])
        yield app
        # セッション終了時に明示的にクリーンアップを試みる
        try:
            app.processEvents()
            app.quit()
        except:
            pass
    except Exception as e:
        # エラーが発生しても続行
        logger.error(f"QApplicationの作成中にエラー: {e}")
        yield None

# 各テスト実行前の共通処理
@pytest.fixture(autouse=True)
def run_around_tests():
    """各テストの前後に必ず実行される処理"""
    # テスト実行前の処理
    warnings.filterwarnings("ignore", category=Warning)
    
    # テストを実行
    yield
    
    # テスト実行後の処理（クリーンアップ）
    if QApplication.instance():
        try:
            QApplication.instance().processEvents()
        except:
            pass 

@pytest.fixture
def qtbot(request):
    """QtBotインスタンスを提供"""
    from pytestqt.qtbot import QtBot
    return QtBot(request) 

# 必要に応じてフィクスチャーを追加
@pytest.fixture
def mock_settings():
    """設定マネージャーのモック"""
    class MockSettings:
        def __init__(self):
            self.settings = {}
            
        def get(self, key, default=None):
            return self.settings.get(key, default)
            
        def set(self, key, value):
            self.settings[key] = value
            
        def save(self):
            pass
    
    return MockSettings()


@pytest.fixture
def mock_ocr_controller():
    """OCRコントローラーのモック"""
    class MockOcrController(QObject):
        text_extracted = pyqtSignal(str, str)
        processing_progress = pyqtSignal(str, int, int)
        all_completed = pyqtSignal()
        
        def __init__(self, settings=None):
            super().__init__()
            self.settings = settings
            self.started = False
            
        def start_ocr(self, image_paths, region_detector=None):
            self.started = True
            # すぐに完了シグナルを発行（テスト用）
            for path in image_paths:
                self.text_extracted.emit(path, f"OCRテキスト: {os.path.basename(path)}")
            self.all_completed.emit()
            
        def cancel(self):
            self.started = False
    
    return MockOcrController()


@pytest.fixture
def mock_prediction_controller():
    """予測コントローラーのモック"""
    class MockPredictionController(QObject):
        output = pyqtSignal(str)
        file_progress = pyqtSignal(str, int, int)
        finished = pyqtSignal(int, dict)
        
        def __init__(self, settings=None, model_manager=None):
            super().__init__()
            self.settings = settings
            self.model_manager = model_manager
            self.started = False
            
        def start(self, model_path, image_dir, conf, scan_subfolders, output_dir):
            self.started = True
            # 処理中とみなす
            
        def cancel(self):
            self.started = False
            
        def simulate_progress(self, file_path, current, total):
            """テスト用の進捗シミュレーション"""
            self.file_progress.emit(file_path, current, total)
            
        def simulate_finish(self, code=0, results=None):
            """テスト用の完了シミュレーション"""
            if results is None:
                results = {}
            self.finished.emit(code, results)
    
    return MockPredictionController()


@pytest.fixture
def mock_model_manager():
    """モデルマネージャーのモック"""
    class MockModelManager:
        def __init__(self):
            self.models = {
                "プリセットモデル": {
                    "model1.pt": {"name": "model1.pt", "type": "YOLOv8"},
                    "model2.pt": {"name": "model2.pt", "type": "YOLOv8"}
                }
            }
            
        def categories(self):
            return list(self.models.keys())
            
        def entries(self, category):
            return list(self.models.get(category, {}).items())
    
    return MockModelManager() 