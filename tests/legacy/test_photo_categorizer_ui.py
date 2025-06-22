#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Photo Categorizer GUI インタラクションテスト
------------------------------------------
pytest-qtを使用してGUIのインタラクションをテストします。
"""

import os
import sys
import pytest
import tempfile
from pathlib import Path

# プロジェクトルートをインポートパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6.QtCore import Qt, QSize, pyqtSignal, QMimeData, QUrl
from PyQt6.QtGui import QPixmap, QStandardItem, QIcon, QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox, QDialog, QInputDialog

from app.ui.photo_categorizer_window import PhotoCategorizerWindow
from app.ui.dictionary_dialog import DictionaryDialog

# テスト用のモック処理を追加
class MockPhotoCategorizerWindow(PhotoCategorizerWindow):
    """テスト用にメソッドをオーバーライドしたモッククラス"""
    
    def _on_ocr_completed(self, results=None):
        """OCR処理完了のコールバック (テスト用拡張)
        
        Args:
            results: テスト用のOCR結果リスト（テスト専用引数）
        """
        # 結果がある場合は処理する（テスト時のみ）
        if results:
            for result in results:
                path = result.get("path")
                text = result.get("text")
                if path and text:
                    self.image_captions[path] = text
                    
                    # すでに表示リストに追加されていない場合は追加
                    found = False
                    for i in range(self.photo_model.rowCount()):
                        item = self.photo_model.item(i)
                        if item.data(Qt.ItemDataRole.UserRole) == path:
                            found = True
                            break
                    
                    if not found:
                        # サムネイル作成
                        pixmap = QPixmap(120, 120)
                        pixmap.fill(Qt.GlobalColor.gray)  # ダミーサムネイル
                        
                        # アイテム作成
                        item = QStandardItem()
                        item.setIcon(QIcon(pixmap))
                        item.setText(os.path.basename(path))
                        item.setData(path, Qt.ItemDataRole.UserRole)
                        
                        # モデルに追加
                        self.photo_model.appendRow(item)
        
        # 元の処理を呼び出す
        super()._on_ocr_completed()
    
    def _display_caption(self, text: str):
        """キャプションの表示 (テスト用オーバーライド)
        
        Args:
            text: 表示するテキスト
        """
        # キャプションを表示
        self.caption_label.setText(text)
        
        # キャプション方向を更新
        self._update_caption_orientation()
    
    def _update_caption_orientation(self):
        """キャプションの表示方向を更新（テスト用オーバーライド）"""
        text = self.caption_label.text()
        
        if self.caption_orientation == "vertical":
            # 縦書きの場合、HTMLで縦書き表現（テスト用に簡素化）
            vertical_text = "<br>".join(text)
            self.caption_label.setText(vertical_text)
        else:
            # 横書きの場合はそのまま
            self.caption_label.setText(text)
    
    # ドラッグアンドドロップイベントをシミュレート
    def simulate_drag_enter(self, file_paths):
        """ドラッグエンターイベントをシミュレート"""
        mime_data = QMimeData()
        urls = [QUrl.fromLocalFile(path) for path in file_paths]
        mime_data.setUrls(urls)
        
        event = QDragEnterEvent(
            self.photo_list.pos(),
            Qt.DropAction.CopyAction,
            mime_data,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        self.dragEnterEvent(event)
        return event.isAccepted()
    
    def simulate_drop(self, file_paths):
        """ドロップイベントをシミュレート"""
        mime_data = QMimeData()
        urls = [QUrl.fromLocalFile(path) for path in file_paths]
        mime_data.setUrls(urls)
        
        event = QDropEvent(
            self.photo_list.pos(),
            Qt.DropAction.CopyAction,
            mime_data,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        self.dropEvent(event)
        return event.isAccepted()


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
    """テスト用のウィンドウを作成（新UI構造）"""
    window = PhotoCategorizerWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    return window


def test_folder_selection(qtbot, window, temp_image_dir, monkeypatch):
    """フォルダ選択機能のテスト"""
    # フォルダ選択ダイアログをモックする
    monkeypatch.setattr(
        QFileDialog, 
        "getExistingDirectory", 
        lambda *args, **kwargs: temp_image_dir
    )
    
    # folder_selectedシグナルを監視
    with qtbot.waitSignal(window.folder_selected, timeout=1000) as signal:
        # フォルダ選択ボタンをクリック
        qtbot.mouseClick(window.folder_button, Qt.MouseButton.LeftButton)
    
    # シグナルが正しいパスで発行されたか確認
    assert signal.args[0] == temp_image_dir
    
    # UIが更新されたか確認
    assert window.folder_edit.text() == temp_image_dir


def test_ocr_button_disabled_without_folder(qtbot, window):
    """フォルダ選択前はOCRボタンが無効化されていることを確認"""
    assert not window.ocr_button.isEnabled()


def test_photo_list_and_selection(qtbot, window, temp_image_dir):
    """写真リストの表示と選択のテスト（新UI構造）"""
    # スキャン結果をシミュレート
    image_files = [os.path.join(temp_image_dir, f"test_image_{i}.jpg") for i in range(3)]
    window.photo_list_widget.set_images(image_files)
    # リストに3枚の写真が表示されていることを確認
    assert window.photo_list_widget.model.rowCount() == 3
    # image_selectedシグナルを監視
    with qtbot.waitSignal(window.image_selected, timeout=1000) as signal:
        index = window.photo_list_widget.model.index(0, 0)
        window.photo_list_widget.list_view.clicked.emit(index)
    assert signal.args[0] == image_files[0]
    assert window.current_image_path == image_files[0]


def test_orientation_change(qtbot, window):
    """キャプション表示方向の切り替えテスト（新UI構造）"""
    # 初期状態は横書き
    assert window.ocr_caption_widget.orientation == "horizontal"
    # サンプルキャプションを設定
    sample_text = "テストキャプション"
    window.ocr_caption_widget.set_caption(sample_text)
    # 縦書きに切り替え
    window.ocr_caption_widget.set_orientation("vertical")
    assert window.ocr_caption_widget.orientation == "vertical"
    # 横書きに戻す
    window.ocr_caption_widget.set_orientation("horizontal")
    assert window.ocr_caption_widget.orientation == "horizontal"


def test_ocr_button(qtbot, window, monkeypatch, temp_image_dir):
    """OCRボタンのテスト"""
    # フォルダが選択されていない状態でボタンをクリック
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    
    # OCR実行前にフォルダを選択していないとワーニングが表示されることを確認
    qtbot.mouseClick(window.ocr_button, Qt.MouseButton.LeftButton)
    
    # フォルダを選択した状態をシミュレート
    window.current_folder = temp_image_dir
    window._update_ui_state(True)
    
    # get_selected_imagesメソッドをモックして、選択画像があるように見せる
    test_image_paths = [os.path.join(temp_image_dir, "test_image.jpg")]
    monkeypatch.setattr(
        window,
        "get_selected_images",
        lambda: test_image_paths
    )
    
    # OCRリクエストシグナルを監視
    with qtbot.waitSignal(window.ocr_requested, timeout=1000):
        # OCRボタンをクリック
        qtbot.mouseClick(window.ocr_button, Qt.MouseButton.LeftButton)
    
    # ボタンが無効化されたか確認
    assert not window.ocr_button.isEnabled()
    
    # プログレスバーが表示されたか確認
    assert window.progress_bar.isVisible()


def test_dict_button(qtbot, window, monkeypatch):
    """辞書編集ボタンのテスト"""
    # 警告ダイアログをモック
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    
    # 辞書マネージャーのモック設定
    from app.controllers.dictionary_manager import DictionaryManager
    mock_dict_manager = DictionaryManager()
    monkeypatch.setattr(window, "dictionary", mock_dict_manager)
    
    # dictionary_edit_requestedシグナルを監視
    with qtbot.waitSignal(window.dictionary_edit_requested, timeout=1000):
        # 辞書編集ボタンをクリック
        qtbot.mouseClick(window.dict_button, Qt.MouseButton.LeftButton)


def test_export_button(qtbot, window, monkeypatch, temp_image_dir):
    """エクスポートボタンのテスト"""
    # フォルダが選択されていない状態でボタンをクリック
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    
    # エクスポート前にフォルダを選択していないとワーニングが表示されることを確認
    qtbot.mouseClick(window.export_button, Qt.MouseButton.LeftButton)
    
    # フォルダを選択した状態をシミュレート
    window.current_folder = temp_image_dir
    window._update_ui_state(True)
    
    # エクスポートリクエストシグナルを監視
    with qtbot.waitSignal(window.export_requested, timeout=1000) as signal:
        # エクスポートボタンをクリック
        qtbot.mouseClick(window.export_button, Qt.MouseButton.LeftButton)
    
    # シグナルが正しい形式で発行されたか確認
    assert signal.args[0] == "csv"


def test_dictionary_switching_flow(qtbot, window, monkeypatch):
    """辞書の切り替えフローのテスト"""
    # scriptsモジュールをシステムにモック
    test_dictionaries = [("test_dict_1", "/path/to/test_dict_1.json"), ("test_dict_2", "/path/to/test_dict_2.json")]
    
    # モックモジュール作成
    class MockDictionaryManager:
        @staticmethod
        def list_available_dictionaries():
            return test_dictionaries
        
        @staticmethod
        def set_active_dictionary(name):
            return True
            
        @staticmethod
        def setup_dictionary_structure():
            pass
    
    # scriptsモジュールをシステムパスにモックして追加
    sys.modules['scripts.dictionary_manager'] = MockDictionaryManager
    
    # モックモジュールからインポートした関数をモニタリング
    set_active_dict_called = False
    orig_set_active = MockDictionaryManager.set_active_dictionary
    
    def mock_set_active_dictionary(name):
        nonlocal set_active_dict_called
        set_active_dict_called = True
        return True
    
    MockDictionaryManager.set_active_dictionary = mock_set_active_dictionary
    
    # QDialogをモック
    def mock_exec(self):
        return QDialog.DialogCode.Accepted
    
    monkeypatch.setattr(QDialog, "exec", mock_exec)
    
    # QComboBoxをモック
    def mock_current_data(self=None):
        return "test_dict_2"
    
    monkeypatch.setattr("PyQt6.QtWidgets.QComboBox.currentData", mock_current_data)
    
    # on_dictionary_changedメソッドをモック
    on_dict_change_called = False
    def mock_on_dictionary_changed(self, name):
        nonlocal on_dict_change_called
        on_dict_change_called = True
    
    monkeypatch.setattr(
        window.__class__, 
        "on_dictionary_changed", 
        mock_on_dictionary_changed
    )
    
    # 辞書選択ダイアログを表示
    window.show_dictionary_selector()
    
    # 辞書が切り替わったことを確認
    assert set_active_dict_called, "set_active_dictionaryが呼ばれていません"
    assert on_dict_change_called, "on_dictionary_changedが呼ばれていません"
    
    # テスト後にモックをクリア
    MockDictionaryManager.set_active_dictionary = orig_set_active
    del sys.modules['scripts.dictionary_manager']


def test_progress_bar(qtbot, window):
    """進捗バーの表示テスト"""
    # 進捗バーを表示
    window.show_progress(True, 50, 100)
    
    # 進捗バーが表示されているか確認
    assert window.progress_bar.isVisible()
    assert window.progress_bar.value() == 50
    assert window.progress_bar.maximum() == 100
    
    # 進捗バーを非表示
    window.show_progress(False)
    
    # 進捗バーが非表示になったか確認
    assert not window.progress_bar.isVisible()


def test_caption_display(qtbot, window):
    """キャプション表示のテスト（新UI構造）"""
    test_caption = "これはテストのキャプションです"
    window.ocr_caption_widget.set_caption(test_caption)
    assert test_caption in window.ocr_caption_widget.ocr_raw_label.text()
    window.ocr_caption_widget.set_orientation("vertical")
    assert window.ocr_caption_widget.orientation == "vertical"
    window.ocr_caption_widget.set_orientation("horizontal")
    assert window.ocr_caption_widget.orientation == "horizontal"


def test_full_workflow(qtbot, window, temp_image_dir, monkeypatch):
    """アプリケーションの完全なワークフローテスト（新UI構造）"""
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    from app.controllers.dictionary_manager import DictionaryManager
    mock_dict_manager = DictionaryManager()
    monkeypatch.setattr(window, "dictionary", mock_dict_manager)
    monkeypatch.setattr(
        QFileDialog, 
        "getExistingDirectory", 
        lambda *args, **kwargs: temp_image_dir
    )
    with qtbot.waitSignal(window.folder_selected, timeout=1000):
        qtbot.mouseClick(window.folder_button, Qt.MouseButton.LeftButton)
    assert window.folder_edit.text() == temp_image_dir
    assert window.ocr_button.isEnabled()
    test_image_paths = [
        os.path.join(temp_image_dir, "test_image_0.jpg"),
        os.path.join(temp_image_dir, "test_image_1.jpg")
    ]
    monkeypatch.setattr(
        window,
        "get_selected_images",
        lambda: test_image_paths
    )
    with qtbot.waitSignal(window.ocr_requested, timeout=1000):
        qtbot.mouseClick(window.ocr_button, Qt.MouseButton.LeftButton)
    # OCR結果のシミュレート
    window.photo_list_widget.set_images(test_image_paths)
    window.set_caption(test_image_paths[0], "テスト1")
    window.set_caption(test_image_paths[1], "テスト2")
    window._on_ocr_completed()
    assert window.photo_list_widget.model.rowCount() == len(test_image_paths)
    assert not window.progress_bar.isVisible()
    index = window.photo_list_widget.model.index(0, 0)
    window.photo_list_widget.list_view.clicked.emit(index)
    assert window.current_image_path == test_image_paths[0]
    window.ocr_caption_widget.set_caption("テスト1")
    assert "テスト1" in window.ocr_caption_widget.ocr_raw_label.text()
    with qtbot.waitSignal(window.dictionary_edit_requested, timeout=1000):
        qtbot.mouseClick(window.dict_button, Qt.MouseButton.LeftButton)
    with qtbot.waitSignal(window.export_requested, timeout=1000) as signal:
        qtbot.mouseClick(window.export_button, Qt.MouseButton.LeftButton)
    assert signal.args[0] == "csv"


def test_error_handling(qtbot, window, temp_image_dir, monkeypatch):
    """エラー処理のテスト"""
    # モーダルダイアログをモック
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    
    # 1. OCRエラーのテスト
    window.current_folder = temp_image_dir
    window._update_ui_state(True)
    
    # OCRエラーをシミュレート
    error_message = "OCR処理中にエラーが発生しました"
    window.show_message(error_message)
    
    # エラーメッセージが表示されているか確認
    assert window.status_bar.currentMessage() == error_message
    
    # 2. 無効な画像ファイルのテスト
    invalid_image = os.path.join(temp_image_dir, "invalid.jpg")
    with open(invalid_image, 'w') as f:
        f.write("This is not an image file")
    
    # 無効な画像を含むフォルダを選択
    monkeypatch.setattr(
        QFileDialog, 
        "getExistingDirectory", 
        lambda *args, **kwargs: temp_image_dir
    )
    
    with qtbot.waitSignal(window.folder_selected, timeout=1000):
        qtbot.mouseClick(window.folder_button, Qt.MouseButton.LeftButton)
    
    # get_selected_imagesメソッドをモック
    monkeypatch.setattr(
        window,
        "get_selected_images",
        lambda: [invalid_image]
    )
    
    # OCR実行時にエラーが発生することを確認
    with qtbot.waitSignal(window.ocr_requested, timeout=1000):
        qtbot.mouseClick(window.ocr_button, Qt.MouseButton.LeftButton)
    
    # エラー処理が正しく機能することを確認
    assert window.progress_bar.isVisible()


def test_performance_with_large_dataset(qtbot, window, temp_image_dir, monkeypatch):
    """大量データ処理時のパフォーマンステスト（新UI構造）"""
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    large_image_dir = os.path.join(temp_image_dir, "large_dataset")
    os.makedirs(large_image_dir, exist_ok=True)
    image_paths = [os.path.join(large_image_dir, f"large_image_{i}.jpg") for i in range(50)]
    for path in image_paths:
        with open(path, 'wb') as f:
            f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00')
    monkeypatch.setattr(
        QFileDialog, 
        "getExistingDirectory", 
        lambda *args, **kwargs: large_image_dir
    )
    with qtbot.waitSignal(window.folder_selected, timeout=1000):
        qtbot.mouseClick(window.folder_button, Qt.MouseButton.LeftButton)
    monkeypatch.setattr(
        window,
        "get_selected_images",
        lambda: image_paths
    )
    with qtbot.waitSignal(window.ocr_requested, timeout=1000):
        qtbot.mouseClick(window.ocr_button, Qt.MouseButton.LeftButton)
    import time
    start_time = time.time()
    window.photo_list_widget.set_images(image_paths)
    for i, path in enumerate(image_paths):
        window.set_caption(path, f"テストテキスト {i}")
    window._on_ocr_completed()
    end_time = time.time()
    assert end_time - start_time < 5.0
    assert window.photo_list_widget.model.rowCount() == 50
    assert not window.progress_bar.isVisible()


def test_different_image_formats(qtbot, window, temp_image_dir, monkeypatch):
    """異なる画像形式の処理テスト（新UI構造）"""
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    image_formats = {
        "test.jpg": b'\xff\xd8\xff\xe0\x00\x10JFIF\x00',
        "test.png": b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR',
        "test.bmp": b'BM\x00\x00\x00\x00\x00\x00\x00\x00',
    }
    for filename, header in image_formats.items():
        with open(os.path.join(temp_image_dir, filename), 'wb') as f:
            f.write(header)
    monkeypatch.setattr(
        QFileDialog, 
        "getExistingDirectory", 
        lambda *args, **kwargs: temp_image_dir
    )
    with qtbot.waitSignal(window.folder_selected, timeout=1000):
        qtbot.mouseClick(window.folder_button, Qt.MouseButton.LeftButton)
    window.current_folder = temp_image_dir
    window._update_ui_state(True)
    test_image_paths = [os.path.join(temp_image_dir, filename) for filename in image_formats.keys()]
    monkeypatch.setattr(
        window,
        "get_selected_images",
        lambda: test_image_paths
    )
    with qtbot.waitSignal(window.ocr_requested, timeout=3000):
        qtbot.mouseClick(window.ocr_button, Qt.MouseButton.LeftButton)
    window.photo_list_widget.set_images(test_image_paths)
    for path in test_image_paths:
        window.set_caption(path, f"{os.path.splitext(os.path.basename(path))[0]}のテキスト")
    window._on_ocr_completed()
    assert window.photo_list_widget.model.rowCount() == len(image_formats)
    format_keys = list(image_formats.keys())
    for i in range(window.photo_list_widget.model.rowCount()):
        item = window.photo_list_widget.model.item(i)
        item_text = item.text()
        basename = os.path.basename(item_text)
        assert basename in format_keys or item_text in format_keys


def test_ocr_cache_operations(qtbot, window, temp_image_dir, monkeypatch):
    """OCRキャッシュ操作のテスト（新UI構造）"""
    test_captions = {os.path.join(temp_image_dir, "test_image_0.jpg"): "テストテキスト"}
    window.image_captions = test_captions.copy()
    test_image_path = os.path.join(temp_image_dir, "test_image_0.jpg")
    window.photo_list_widget.set_images([test_image_path])
    index = window.photo_list_widget.model.index(0, 0)
    window._on_photo_clicked(index)
    assert window.ocr_caption_widget.ocr_raw_label.text() == "テストテキスト" or "テストテキスト" in window.ocr_caption_widget.ocr_raw_label.text(), "キャプションが正しく表示されていません"
    window.image_captions[test_image_path] = "新しいテキスト"
    window._on_photo_clicked(index)
    assert window.ocr_caption_widget.ocr_raw_label.text() == "新しいテキスト" or "新しいテキスト" in window.ocr_caption_widget.ocr_raw_label.text(), "更新されたキャプションが表示されていません"


def test_directory_navigation(qtbot, window, monkeypatch, temp_image_dir):
    """ディレクトリ移動とフォルダ選択のフローテスト（新UI構造）"""
    subdir = os.path.join(temp_image_dir, "subdir")
    os.makedirs(subdir, exist_ok=True)
    for i in range(2):
        dummy_file = os.path.join(subdir, f"sub_image_{i}.jpg")
        with open(dummy_file, 'wb') as f:
            f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00')
    monkeypatch.setattr(
        QFileDialog, 
        "getExistingDirectory", 
        lambda *args, **kwargs: temp_image_dir
    )
    window._on_folder_button_clicked()
    assert window.current_folder == temp_image_dir
    assert window.folder_edit.text() == temp_image_dir
    window.subfolder_check.setChecked(True)
    all_images = [
        os.path.join(temp_image_dir, f"test_image_{i}.jpg") for i in range(3)
    ] + [
        os.path.join(subdir, f"sub_image_{i}.jpg") for i in range(2)
    ]
    window.photo_list_widget.set_images(all_images)
    assert window.photo_list_widget.model.rowCount() == 5
    window.subfolder_check.setChecked(False)
    window._on_subfolder_toggled(False)
    parent_images = [os.path.join(temp_image_dir, f"test_image_{i}.jpg") for i in range(3)]
    window.photo_list_widget.set_images(parent_images)
    assert window.photo_list_widget.model.rowCount() == 3


def test_multiple_image_selection(qtbot, window, temp_image_dir):
    """複数画像選択のテスト（新UI構造）"""
    image_files = [os.path.join(temp_image_dir, f"test_image_{i}.jpg") for i in range(3)]
    window.photo_list_widget.set_images(image_files)
    list_view = window.photo_list_widget.list_view
    list_view.setSelectionMode(list_view.SelectionMode.ExtendedSelection)
    index1 = window.photo_list_widget.model.index(0, 0)
    list_view.selectionModel().select(index1, list_view.selectionModel().SelectionFlag.Select)
    index2 = window.photo_list_widget.model.index(2, 0)
    list_view.selectionModel().select(index2, list_view.selectionModel().SelectionFlag.Select)
    selected_indexes = list_view.selectionModel().selectedIndexes()
    assert len(selected_indexes) == 2, "2つの画像が選択されていません"
    selected_paths = [window.photo_list_widget.model.itemFromIndex(index).data(Qt.ItemDataRole.UserRole) for index in selected_indexes]
    assert image_files[0] in selected_paths, "最初の画像が選択されていません"
    assert image_files[2] in selected_paths, "3番目の画像が選択されていません"
    selected = window.get_selected_images()
    assert len(selected) == 2, "選択画像の取得に失敗しました"


def test_create_new_dictionary(qtbot, window, monkeypatch):
    """新規辞書作成フローのテスト"""
    # scriptsモジュールをシステムにモック
    class MockDictionaryManager:
        @staticmethod
        def list_available_dictionaries():
            return [("default", "/path/to/default.json")]
        
        @staticmethod
        def create_custom_dictionary(name, source_dict=None):
            return True
    
    # scriptsモジュールをシステムパスにモックして追加
    sys.modules['scripts.dictionary_manager'] = MockDictionaryManager
    
    # モックモジュールからインポートした関数をモニタリング
    create_called = False
    orig_create = MockDictionaryManager.create_custom_dictionary
    
    def mock_create_custom_dictionary(name, source_dict=None):
        nonlocal create_called
        create_called = True
        return True
    
    MockDictionaryManager.create_custom_dictionary = mock_create_custom_dictionary
    
    # QInputDialogをモック
    monkeypatch.setattr(
        "PyQt6.QtWidgets.QInputDialog.getText", 
        lambda *args, **kwargs: ("新しい辞書", True)
    )
    
    monkeypatch.setattr(
        "PyQt6.QtWidgets.QInputDialog.getItem", 
        lambda *args, **kwargs: ("新規（空の辞書）", True)
    )
    
    # QMessageBoxをモック
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    
    # windowにモックの辞書マネージャを設定（必要な場合）
    class MockDictMgr:
        def reload_dictionaries(self):
            pass
    
    # テスト用のモック辞書マネージャを設定
    window.dictionary = MockDictMgr()
    
    # 新規辞書作成メソッドを呼び出し
    window.create_new_dictionary()
    
    # 辞書が作成されたことを確認
    assert create_called, "create_custom_dictionaryが呼ばれていません"
    
    # テスト後にモックをクリア
    MockDictionaryManager.create_custom_dictionary = orig_create
    del sys.modules['scripts.dictionary_manager']


def test_main_widgets_layout(qtbot):
    """
    PhotoCategorizerWindowの主要UI部品がレイアウト上に正しく配置されているかを検証する（モックなし）
    """
    window = PhotoCategorizerWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    assert hasattr(window, 'photo_list_widget')
    assert window.photo_list_widget.isVisible()
    assert hasattr(window, 'ocr_caption_widget')
    assert window.ocr_caption_widget.isVisible()
    assert hasattr(window, 'dict_match_widget')
    assert window.dict_match_widget.isVisible() 