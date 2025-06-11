import os
import sys
import subprocess
import json
from PyQt6.QtWidgets import QMessageBox
from src.excel_utils import close_excel_file

def reopen_excel_with_fix(last_save_path, config_path, parent=None):
    """
    Excelファイルを再オープンし、画像プロパティ修正・（必要なら印刷設定も）を適用する。
    parent: QMessageBoxの親ウィジェット
    """
    if not last_save_path or not os.path.exists(last_save_path):
        QMessageBox.warning(parent, "エラー", "前回のExcel出力ファイルが見つかりません")
        return
    # Excelで開いていれば閉じる
    close_excel_file(last_save_path)
    # 画像プロパティ修正
    py_exe = sys.executable
    fix_script = os.path.join(os.path.dirname(__file__), "..", "fix_excel_images.py")
    try:
        subprocess.run([py_exe, fix_script, last_save_path], check=True)
    except Exception as e:
        QMessageBox.warning(parent, "エラー", f"画像プロパティ修正に失敗: {e}")
        return
    # 印刷設定適用（必要なら有効化）
    # fix_print_script = os.path.join(os.path.dirname(__file__), "..", "fix_excel_print_settings.py")
    # try:
    #     subprocess.run([py_exe, fix_print_script, last_save_path], check=True)
    # except Exception as e:
    #     QMessageBox.warning(parent, "エラー", f"印刷設定適用に失敗: {e}")
    #     return
    # Excelで再オープン
    try:
        os.startfile(last_save_path)
    except Exception as e:
        QMessageBox.warning(parent, "エラー", f"Excelファイルの再オープンに失敗: {e}")
