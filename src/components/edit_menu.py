from PyQt6.QtWidgets import QMenu, QDialog, QVBoxLayout
from PyQt6.QtGui import QAction

from src.actions.ocr_detection_action import run_ocr_detection  # 独立モジュール

def create_edit_menu(parent, dictionary_manager):
    edit_menu = QMenu("編集", parent)

    # ロールマッピング編集
    act_edit_role_mapping = QAction("ロールマッピング編集", parent)
    def open_role_mapping_dialog():
        from src.widgets.dictionary_mapping_widget import DictionaryMappingWidget
        dlg = QDialog(parent)
        dlg.setWindowTitle("ロールマッピング編集")
        layout = QVBoxLayout(dlg)
        mapping_widget = DictionaryMappingWidget(dlg)
        layout.addWidget(mapping_widget)
        dlg.setLayout(layout)
        dlg.resize(800, 600)
        dlg.exec()
    act_edit_role_mapping.triggered.connect(open_role_mapping_dialog)
    edit_menu.addAction(act_edit_role_mapping)

    # 辞書レコード編集
    act_edit_dictionary = QAction("辞書レコード編集", parent)
    def open_dictionary_editor_dialog():
        from src.widgets.dictionary_editor_dialog import DictionaryListEditorDialog
        if hasattr(parent, '_dictionary_editor_dialog') and parent._dictionary_editor_dialog is not None:
            try:
                parent._dictionary_editor_dialog.close()
            except Exception:
                pass
        parent._dictionary_editor_dialog = DictionaryListEditorDialog(dictionary_manager, parent)
        parent._dictionary_editor_dialog.show()
    act_edit_dictionary.triggered.connect(open_dictionary_editor_dialog)
    edit_menu.addAction(act_edit_dictionary)

    # --- OCR測点検出 ---------------------------------------------------
    act_ocr_detect = QAction("OCR測点検出", parent)
    act_ocr_detect.triggered.connect(lambda: run_ocr_detection(parent))
    edit_menu.addAction(act_ocr_detect)

    return edit_menu
