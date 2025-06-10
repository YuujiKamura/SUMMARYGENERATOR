#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ユーザー辞書エディタのテスト
"""

import os
import sys
import json
import tempfile
from pathlib import Path

# プロジェクトルートをインポートパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.controllers.dictionary_manager import DictionaryManager
from scripts.dictionary_manager import setup_dictionary_structure, create_custom_dictionary, list_available_dictionaries, set_active_dictionary
import logging

# PyQt6のインポート
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# ロギング設定
logging.basicConfig(level=logging.INFO)

def test_dictionary_editor():
    """辞書エディタの編集と保存をテスト"""
    print("\n=== 辞書エディタのテスト ===")
    
    # 1. テスト用の辞書を準備
    setup_dictionary_structure()
    test_dict_name = "test_editor_dict"
    create_custom_dictionary(test_dict_name)
    set_active_dictionary(test_dict_name)
    
    # 2. 辞書マネージャーを初期化
    dict_manager = DictionaryManager()
    dict_manager.set_project(test_dict_name)
    
    # 辞書の初期状態を確認
    print(f"\n辞書の初期状態:")
    print(f"  レコード数: {len(dict_manager.records)}")
    for dict_type, entries in dict_manager.dictionaries.items():
        print(f"  {dict_type}: {len(entries)} 項目")
    
    # 3. 辞書に項目を追加
    print("\n項目を追加します...")
    
    # 工種を追加
    dict_manager.add_entry("category", "テスト工種1")
    dict_manager.add_entry("category", "テスト工種2")
    
    # 種別を追加
    dict_manager.add_entry("type", "テスト種別1")
    dict_manager.add_entry("type", "テスト種別2")
    
    # 保存
    dict_manager.save_dictionaries()
    
    # 4. 変更後の辞書を確認
    print("\n変更後の辞書:")
    print(f"  レコード数: {len(dict_manager.records)}")
    for dict_type, entries in dict_manager.dictionaries.items():
        print(f"  {dict_type}: {len(entries)} 項目")
        if len(entries) > 0:
            print(f"    項目: {entries}")
    
    # 5. 辞書をリロードして永続化されたか確認
    print("\n辞書を再読み込み...")
    new_dict_manager = DictionaryManager()
    new_dict_manager.set_project(test_dict_name)
    
    print("\n再読み込み後の辞書:")
    print(f"  レコード数: {len(new_dict_manager.records)}")
    for dict_type, entries in new_dict_manager.dictionaries.items():
        print(f"  {dict_type}: {len(entries)} 項目")
        if len(entries) > 0:
            print(f"    項目: {entries}")
    
    # 6. 変更が保存されたかチェック
    is_category_saved = "テスト工種1" in new_dict_manager.dictionaries["category"] and "テスト工種2" in new_dict_manager.dictionaries["category"]
    is_type_saved = "テスト種別1" in new_dict_manager.dictionaries["type"] and "テスト種別2" in new_dict_manager.dictionaries["type"]
    
    if is_category_saved and is_type_saved:
        print("\n✓ 辞書の変更が正しく保存されています")
    else:
        print("\n✗ 辞書の変更が正しく保存されていません")
        if not is_category_saved:
            print("  - 工種の項目が保存されていません")
        if not is_type_saved:
            print("  - 種別の項目が保存されていません")
    
    return is_category_saved and is_type_saved

if __name__ == "__main__":
    # QApplication インスタンスを作成（GUI表示用）
    app = QApplication(sys.argv)
    
    # テスト実行
    test_dictionary_editor()
    
    # アプリケーション終了
    sys.exit(0) 