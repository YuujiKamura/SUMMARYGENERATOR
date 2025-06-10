from PyQt6.QtWidgets import QFileDialog, QMessageBox, QInputDialog
from PyQt6.QtGui import QAction
import os
import json

def add_project_menu_actions(widget):
    """
    SummaryGeneratorWidgetのメニューバーにプロジェクト管理・管理ファイルセット切り替え・一括コピー・ユーザー辞書編集・バージョン情報を追加
    """
    menubar = widget.menubar
    file_menu = menubar.actions()[0].menu()
    edit_menu = menubar.actions()[1].menu()
    help_menu = menubar.actions()[2].menu()

    # 管理ファイル一括コピー
    act_copy_managed_files = QAction("管理ファイル一括コピー", widget)
    def copy_managed_files():
        dest_dir = QFileDialog.getExistingDirectory(widget, "コピー先ディレクトリを選択")
        if dest_dir:
            try:
                from src.utils.path_manager import path_manager
                path_manager.copy_all_managed_files(dest_dir, overwrite=True)
                QMessageBox.information(widget, "完了", f"管理ファイルを\n{dest_dir}\nにコピーしました。")
            except Exception as e:
                QMessageBox.critical(widget, "エラー", f"コピー中にエラー: {e}")
    act_copy_managed_files.triggered.connect(copy_managed_files)
    file_menu.addAction(act_copy_managed_files)

    # 現在の管理ファイルを集約保存
    act_save_current_managed_files = QAction("現在の管理ファイルを集約保存", widget)
    def save_current_managed_files_action():
        try:
            from src.utils.managed_files_utils import save_current_managed_files
            managed_dir = save_current_managed_files()
            widget.set_status(f"現在の管理ファイルを {managed_dir} に集約保存しました。")
        except Exception as e:
            QMessageBox.critical(widget, "エラー", f"集約保存中にエラー: {e}")
    act_save_current_managed_files.triggered.connect(save_current_managed_files_action)
    file_menu.addAction(act_save_current_managed_files)

    # 管理ファイルセット切り替え
    act_switch_managed_file_set = QAction("管理ファイルセット切り替え", widget)
    def switch_managed_file_set_action():
        managed_base = os.path.abspath(
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..", "..", "managed_files"
            )
        )
        sets = [d for d in os.listdir(managed_base) if os.path.isdir(os.path.join(managed_base, d))]
        if not sets:
            QMessageBox.warning(widget, "管理ファイルセット", "管理ファイルセットがありません。先に集約保存してください。")
            return
        set_name, ok = QInputDialog.getItem(widget, "管理ファイルセット切り替え", "セットを選択:", sets, 0, False)
        if ok and set_name:
            set_dir = os.path.join(managed_base, set_name)
            try:
                from src.utils.managed_files_utils import switch_managed_file_set
                switched_path = switch_managed_file_set(set_dir)
                widget.set_status(f"管理ファイルセットを切り替えました: {switched_path}")
                if hasattr(widget, 'debug_text'):
                    widget.debug_text.setPlainText(f"[管理ファイルセット] {switched_path}")
            except Exception as e:
                QMessageBox.critical(widget, "エラー", f"切り替え中にエラー: {e}")
    act_switch_managed_file_set.triggered.connect(switch_managed_file_set_action)
    file_menu.addAction(act_switch_managed_file_set)

    # プロジェクト管理
    act_project_manager = QAction("プロジェクト管理", widget)
    def open_project_manager():
        from src.widgets.project_manager_dialog import ProjectManagerDialog
        from PyQt6.QtWidgets import QDialog
        managed_base = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "managed_files"))
        dlg = ProjectManagerDialog(managed_base, widget)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            current_project = dlg.get_selected_project()
            if current_project:
                set_dir = os.path.join(managed_base, current_project)
                widget.set_status(f"管理プロジェクトを切り替えました: {set_dir}")
                if hasattr(widget, 'debug_text'):
                    widget.debug_text.setPlainText(f"[管理プロジェクト] {set_dir}")
    act_project_manager.triggered.connect(open_project_manager)
    file_menu.addAction(act_project_manager)

    # ユーザー辞書編集
    act_userdict_edit = QAction("ユーザー辞書編集", widget)
    def open_userdict_editor():
        from src.widgets.dictionary_editor_dialog import DictionaryListEditorDialog
        from src.dictionary_manager import DictionaryManager
        if hasattr(widget, 'userdict_editor') and widget.userdict_editor is not None:
            try:
                widget.userdict_editor.close()
            except Exception:
                pass
        dm = DictionaryManager()
        widget.userdict_editor = DictionaryListEditorDialog(dm, widget)
        widget.userdict_editor.show()
    act_userdict_edit.triggered.connect(open_userdict_editor)
    edit_menu.addAction(act_userdict_edit)

    # バージョン情報
    act_about = QAction("バージョン情報", widget)
    def show_about():
        QMessageBox.information(widget, "バージョン情報", "PhotoCategorizer v1.0")
    act_about.triggered.connect(show_about)
    help_menu.addAction(act_about)
