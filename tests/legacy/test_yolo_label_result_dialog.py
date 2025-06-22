import os
import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QDialog, QTableWidget
from src.widgets.project_manager_dialog import ProjectManagerDialog

# pytest実行時は --timeout=60 などでタイムアウトを明示的に指定することを推奨

@pytest.fixture
def dialog(qtbot):
    managed_base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../managed_files"))
    dlg = ProjectManagerDialog(managed_base_dir, test_mode=True)
    qtbot.addWidget(dlg)
    dlg.show()
    qtbot.waitExposed(dlg)
    return dlg

def test_yolo_label_result_dialog_shows_and_preview(qtbot, dialog):
    # currentプロジェクトを選択
    items = dialog.list_widget.findItems("current", Qt.MatchFlag.MatchExactly)
    assert items, "currentプロジェクトが見つからない"
    dialog.list_widget.setCurrentItem(items[0])
    # YOLO出力ボタンをクリック
    qtbot.mouseClick(dialog.btn_export_yolo, Qt.MouseButton.LeftButton)
    # ラベリング結果ダイアログが表示されるか確認
    # QDialogが開くまで待つ
    result_dialog = None
    for _ in range(30):
        for w in QApplication.topLevelWidgets():
            if isinstance(w, QDialog) and w.windowTitle().startswith("YOLOラベリング結果一覧"):
                result_dialog = w
                break
        if result_dialog:
            break
        qtbot.wait(200)
    assert result_dialog is not None, "ラベリング結果ダイアログが表示されない"
    # テーブル内容を検証
    table = result_dialog.findChild(QTableWidget)
    assert table is not None, "テーブルが見つからない"
    row_count = table.rowCount()
    assert row_count > 0, "テーブルに行がない"
    # 1行目の内容を確認
    img_cell = table.item(0, 0)
    status_cell = table.item(0, 1)
    label_cell = table.item(0, 2)
    assert img_cell and status_cell and label_cell, "テーブルのセルが空"
    # ダブルクリックでプレビューダイアログが開くか
    qtbot.mouseDClick(table.viewport(), Qt.MouseButton.LeftButton, pos=table.visualItemRect(table.item(0,0)).center())
    preview_dialog = None
    for _ in range(20):
        for w in QApplication.topLevelWidgets():
            if isinstance(w, QDialog) and w.windowTitle().startswith("画像プレビュー"):
                preview_dialog = w
                break
        if preview_dialog:
            break
        qtbot.wait(200)
    assert preview_dialog is not None, "プレビューダイアログが開かない"
    # プレビューダイアログを閉じる
    preview_dialog.accept()
    # 結果ダイアログも閉じる
    result_dialog.accept() 