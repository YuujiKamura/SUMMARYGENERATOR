#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
問題のテストを実行してファイルにログを出力するスクリプト
"""

import sys
import pytest
import os
import traceback
import tempfile
import time

def run_test_with_output():
    """テストを実行し、結果をファイルに出力"""
    # 出力を保存するログファイル
    log_file = "test_debug_output.log"
    
    # 現在の標準出力と標準エラー出力を退避
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    
    try:
        # 出力をファイルにリダイレクト
        with open(log_file, 'w', encoding='utf-8') as f:
            sys.stdout = f
            sys.stderr = f
            
            # テスト情報の出力
            print(f"実行時刻: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Current directory: {os.getcwd()}")
            print(f"Python executable: {sys.executable}")
            print(f"Python version: {sys.version}")
            
            # 問題のテストだけを実行
            test_file = "tests/test_photo_categorizer_ui.py::test_different_image_formats"
            print(f"実行するテスト: {test_file}")
            
            # 詳細なオプションでテストを実行
            result = pytest.main([
                "-v",  # 詳細出力
                "--showlocals",  # ローカル変数を表示
                test_file
            ])
            
            print(f"\nテスト実行結果コード: {result}")
            
            return result
    except Exception as e:
        # エラー発生時は標準出力に戻してからメッセージを表示
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        print(f"Error: {e}")
        print(traceback.format_exc())
        return 1
    finally:
        # 標準出力と標準エラー出力を元に戻す
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        print(f"テスト結果は {log_file} に出力されました")

if __name__ == "__main__":
    exit_code = run_test_with_output()
    sys.exit(exit_code) 