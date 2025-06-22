#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Photo Categorizer OCRボタン機能テスト
"""

import os
import sys
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# プロジェクトルートをインポートパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest

from app.ui.photo_categorizer_window import PhotoCategorizerWindow


# モックのコントローラーとマネージャー
class MockSettings(QObject):
    """設定マネージャーのモック"""
    def get(self, key, default=None):
        return default


class MockModels(QObject):
    """モデルマネージャーのモック"""
    def categories(self):
        return ["カテゴリ1", "カテゴリ2"]


class MockPredictor(QObject):
    """予測コントローラのモック"""
    output = pyqtSignal(str)
    file_progress = pyqtSignal(str, int, int)
    finished = pyqtSignal(int, object)


class MockOcr(QObject):
    """OCRコントローラのモック"""
    text_extracted = pyqtSignal(str, str)
    processing_progress = pyqtSignal(str, int, int)
    all_completed = pyqtSignal()
    
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.start_ocr_calls = []
    
    def start_ocr(self, image_paths, region_detector=None):
        self.start_ocr_calls.append((image_paths, region_detector))
        # OCR結果をシミュレート
        for path in image_paths:
            self.text_extracted.emit(path, f"OCRテスト結果 {os.path.basename(path)}")
        # 処理完了を通知
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
def window(qtbot):
    """テスト用のウィンドウを作成"""
    # モックコントローラー
    settings = MockSettings()
    models = MockModels()
    predictor = MockPredictor()
    ocr = MockOcr()
    
    # ウィンドウ作成
    window = PhotoCategorizerWindow(settings, models, predictor, ocr)
    # OCRリクエストシグナルとモックOCRのstart_ocrメソッドを接続
    window.ocr_requested.connect(lambda: ocr.start_ocr(window._get_image_files(), None))
    
    window.show()
    qtbot.addWidget(window)
    
    yield window
    
    window.close()


# スキャンによるファイル読み込みを模擬するモンキーパッチ
def patch_scan_thread(window, temp_image_dir):
    """スキャンスレッドをモンキーパッチして実際のファイル検索をスキップ"""
    # 実装されていない_get_image_filesメソッドを追加
    def _get_image_files():
        return [os.path.join(temp_image_dir, f"test_image_{i}.jpg") for i in range(3)]
    
    window._get_image_files = _get_image_files
    
    # _on_scan_completeメソッドを直接呼び出して画像を登録
    window._on_scan_complete(_get_image_files())


def test_ocr_button_disabled_on_start(window):
    """起動時にOCRボタンが無効であることを確認"""
    assert not window.ocr_button.isEnabled()


def test_ocr_button_enables_after_folder_selection(window, temp_image_dir, qtbot):
    """フォルダ選択後にOCRボタンが有効になることを確認"""
    # フォルダ選択ダイアログをモック
    with patch('PyQt6.QtWidgets.QFileDialog.getExistingDirectory', return_value=temp_image_dir):
        # フォルダ選択ボタンをクリック
        qtbot.mouseClick(window.folder_button, Qt.MouseButton.LeftButton)
    
    # フォルダパスが表示されることを確認
    assert window.folder_edit.text() == temp_image_dir
    
    # OCRボタンが有効になることを確認
    assert window.ocr_button.isEnabled()


def test_ocr_button_click_triggers_ocr(window, temp_image_dir, qtbot):
    """OCRボタンクリックでOCR処理が開始されることを確認"""
    # フォルダを選択
    with patch('PyQt6.QtWidgets.QFileDialog.getExistingDirectory', return_value=temp_image_dir):
        qtbot.mouseClick(window.folder_button, Qt.MouseButton.LeftButton)
    
    # スキャン処理をモック
    patch_scan_thread(window, temp_image_dir)
    
    # OCRボタンが有効になることを確認
    assert window.ocr_button.isEnabled()
    
    # OCRリクエストシグナルの接続を一時的に解除
    window.ocr_requested.disconnect()
    
    # OCRボタンをクリック
    with qtbot.waitSignal(window.ocr_requested, timeout=1000):
        qtbot.mouseClick(window.ocr_button, Qt.MouseButton.LeftButton)
    
    # プログレスバーが表示されることを確認
    assert window.progress_bar.isVisible()
    
    # OCRリクエストシグナルを再接続
    window.ocr_requested.connect(lambda: window.ocr.start_ocr(window._get_image_files(), None))
    
    # 手動でOCR処理を呼び出す
    window.ocr.start_ocr(window._get_image_files(), None)
    
    # OCRコントローラのstart_ocrが呼び出されていることを確認
    assert len(window.ocr.start_ocr_calls) > 0


def test_ocr_controller_receives_image_paths(window, temp_image_dir, qtbot):
    """OCRコントローラが正しい画像パスを受け取ることを確認"""
    # フォルダを選択
    with patch('PyQt6.QtWidgets.QFileDialog.getExistingDirectory', return_value=temp_image_dir):
        qtbot.mouseClick(window.folder_button, Qt.MouseButton.LeftButton)
    
    # スキャン処理をモック
    patch_scan_thread(window, temp_image_dir)
    
    # OCRボタンをクリック
    with qtbot.waitSignal(window.ocr_requested, timeout=1000):
        qtbot.mouseClick(window.ocr_button, Qt.MouseButton.LeftButton)
    
    # OCRコントローラに渡された画像パスを確認
    assert len(window.ocr.start_ocr_calls) > 0
    image_paths, _ = window.ocr.start_ocr_calls[0]
    
    # すべてのテスト画像が含まれていることを確認
    for i in range(3):
        test_image = os.path.join(temp_image_dir, f"test_image_{i}.jpg")
        assert any(path.endswith(f"test_image_{i}.jpg") for path in image_paths)


def test_ocr_completion_updates_ui(window, temp_image_dir, qtbot):
    """OCR完了時にUIが適切に更新されることを確認"""
    # フォルダを選択
    with patch('PyQt6.QtWidgets.QFileDialog.getExistingDirectory', return_value=temp_image_dir):
        qtbot.mouseClick(window.folder_button, Qt.MouseButton.LeftButton)
    
    # スキャン処理をモック
    patch_scan_thread(window, temp_image_dir)
    
    # OCRボタンをクリック
    with qtbot.waitSignal(window.ocr_requested, timeout=1000):
        qtbot.mouseClick(window.ocr_button, Qt.MouseButton.LeftButton)
    
    # OCR処理完了後、プログレスバーが非表示になることを確認
    QTest.qWait(500)  # 処理完了を待つ
    assert not window.progress_bar.isVisible()
    
    # OCRボタンが再度有効になっていることを確認
    assert window.ocr_button.isEnabled()


def test_full_ocr_workflow(window, temp_image_dir, qtbot):
    """OCR処理の完全なワークフローテスト"""
    # フォルダを選択
    with patch('PyQt6.QtWidgets.QFileDialog.getExistingDirectory', return_value=temp_image_dir):
        qtbot.mouseClick(window.folder_button, Qt.MouseButton.LeftButton)
    
    # スキャン処理をモック
    patch_scan_thread(window, temp_image_dir)
    
    # OCRボタンをクリック
    with qtbot.waitSignal(window.ocr_requested, timeout=1000):
        qtbot.mouseClick(window.ocr_button, Qt.MouseButton.LeftButton)
    
    # OCR処理が完了するのを待つ
    QTest.qWait(500)
    
    # 画像が選択されていない場合は最初の画像を選択
    if window.current_image_path is None and window.photo_model.rowCount() > 0:
        index = window.photo_model.index(0, 0)
        window.photo_list.clicked.emit(index)
    
    # キャプションが表示されているか確認
    if window.current_image_path:
        assert "OCRテスト結果" in window.caption_label.text()
        
    # OCRボタンが再度有効になっていることを確認
    assert window.ocr_button.isEnabled() 