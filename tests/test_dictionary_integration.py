#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ユーザー辞書の選択と変更をテストするスクリプト
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

# ロギング設定
logging.basicConfig(level=logging.INFO)

def test_dictionary_selection_and_editing():
    """辞書選択と編集のテスト"""
    print("\n=== 辞書選択と編集のテスト ===")
    
    # 1. 辞書管理構造をセットアップ
    setup_dictionary_structure()
    
    # 2. 利用可能な辞書を確認
    dictionaries = list_available_dictionaries()
    print(f"利用可能な辞書: {len(dictionaries)}件")
    for name, path in dictionaries:
        print(f"  {name}: {path}")
    
    # 3. テスト用辞書の作成
    test_dict_name = "test_dictionary"
    create_custom_dictionary(test_dict_name)
    print(f"テスト辞書 '{test_dict_name}' を作成しました")
    
    # 4. 辞書選択（アクティブに設定）
    set_active_dictionary(test_dict_name)
    print(f"辞書 '{test_dict_name}' をアクティブに設定しました")
    
    # 5. 辞書マネージャーで辞書を読み込み、内容を確認
    dict_manager = DictionaryManager()
    dict_manager.set_project(test_dict_name)  # 明示的にプロジェクト設定
    print(f"現在のプロジェクト名: {dict_manager.current_project}")
    print(f"辞書内容: {len(dict_manager.records)} レコード")
    for dict_type, entries in dict_manager.dictionaries.items():
        print(f"  {dict_type}: {len(entries)} 項目")
    
    # 6. 辞書に項目を追加
    print("\n項目を追加します...")
    added = dict_manager.add_entry("category", "テスト工種")
    print(f"辞書に項目を追加: {'成功' if added else '失敗'}")
    
    # 辞書の内容を確認
    print("\n追加後の内容:")
    for dict_type, entries in dict_manager.dictionaries.items():
        print(f"  {dict_type}: {len(entries)} 項目")
        if dict_type == "category":
            print(f"    項目: {entries}")
    
    # 7. 保存して終了
    dict_manager.save_dictionaries()
    print("\n保存しました")
    
    # 8. 新しいマネージャーを作成して読み込み
    print("\n新しいマネージャーで読み込みます...")
    new_dict_manager = DictionaryManager()
    new_dict_manager.set_project(test_dict_name)  # 明示的にプロジェクト設定
    
    # 9. 内容を確認
    print(f"現在のプロジェクト名: {new_dict_manager.current_project}")
    print(f"辞書内容: {len(new_dict_manager.records)} レコード")
    for dict_type, entries in new_dict_manager.dictionaries.items():
        print(f"  {dict_type}: {len(entries)} 項目")
        if dict_type == "category":
            print(f"    項目: {entries}")
    
    # 10. 追加した項目があるか確認
    if "テスト工種" in new_dict_manager.dictionaries["category"]:
        print("\n追加した項目「テスト工種」が見つかりました ✓")
    else:
        print("\nエラー: 追加した項目が見つかりません ✗")
    
    return True

if __name__ == "__main__":
    test_dictionary_selection_and_editing() 