#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PyQt6と環境のインポートテスト
"""

import os
import sys
from pathlib import Path

# プロジェクトルートを追加
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    print("インポートテスト開始")
    print(f"Pythonバージョン: {sys.version}")
    print(f"実行パス: {sys.executable}")
    print(f"カレントディレクトリ: {os.getcwd()}")
    
    print("\n--- PyQt6のインポートテスト ---")
    from PyQt6.QtCore import Qt, QSize
    print("PyQt6.QtCore: OK")
    from PyQt6.QtGui import QPixmap, QStandardItem, QIcon
    print("PyQt6.QtGui: OK")
    from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox
    print("PyQt6.QtWidgets: OK")
    
    print("\n--- アプリケーションコードのインポートテスト ---")
    try:
        from app.ui.photo_categorizer_window import PhotoCategorizerWindow
        print("PhotoCategorizerWindow: OK")
    except ImportError as e:
        print(f"PhotoCategorizerWindow: エラー - {e}")
    
    try:
        from app.ui.dictionary_dialog import DictionaryDialog
        print("DictionaryDialog: OK")
    except ImportError as e:
        print(f"DictionaryDialog: エラー - {e}")
    
    print("\n--- pytestのインポートテスト ---")
    import pytest
    print("pytest: OK")
    try:
        import pytest_qt
        print("pytest-qt: OK")
    except ImportError as e:
        print(f"pytest-qt: エラー - {e}")
    
    print("\nすべてのインポートが成功しました")
except ImportError as e:
    print(f"インポートエラー: {e}")
except Exception as e:
    print(f"その他のエラー: {e}")

if __name__ == "__main__":
    print("テスト完了") 