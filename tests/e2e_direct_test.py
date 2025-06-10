#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import unittest
import subprocess
import time
import json

# テストの成功失敗を記録するファイル
RESULT_FILE = os.path.join(os.path.dirname(__file__), "test_results.json")

def run_test_directly(test_name):
    """サブプロセスでテストを直接実行"""
    print(f"テスト '{test_name}' を実行します...")
    
    # テスト実行コマンド
    if test_name == "mini_test":
        cmd = ["python", "tests/mini_test.py"]
    elif test_name == "e2e_save_load":
        cmd = ["python", "-c", """
import sys
import os
sys.path.insert(0, os.path.abspath('.'))
# from tests.e2e_test だと動作しないため、直接インポート
sys.path.insert(0, os.path.join(os.path.abspath('.'), 'tests'))
import e2e_test
import unittest

# テストを実行
suite = unittest.TestSuite()
suite.addTest(e2e_test.TestPhotoCategorizerE2E('test_e2e_save_load_cycle'))
unittest.TextTestRunner(verbosity=2).run(suite)
"""]
    elif test_name == "e2e_basic_workflow":
        cmd = ["python", "-c", """
import sys
import os
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.join(os.path.abspath('.'), 'tests'))
import e2e_test
import unittest

# テストを実行
suite = unittest.TestSuite()
suite.addTest(e2e_test.TestPhotoCategorizerE2E('test_e2e_basic_workflow'))
unittest.TextTestRunner(verbosity=2).run(suite)
"""]
    elif test_name == "e2e_resize_box":
        cmd = ["python", "-c", """
import sys
import os
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.join(os.path.abspath('.'), 'tests'))
import e2e_test
import unittest

# テストを実行
suite = unittest.TestSuite()
suite.addTest(e2e_test.TestPhotoCategorizerE2E('test_e2e_resize_bounding_box'))
unittest.TextTestRunner(verbosity=2).run(suite)
"""]
    elif test_name == "simplest_test":
        cmd = ["python", "tests/simplest_test.py"]
    else:
        print(f"不明なテスト: {test_name}")
        return False

    # 実行
    try:
        start_time = time.time()
        result = subprocess.run(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            timeout=30,  # 30秒でタイムアウト
            text=True
        )
        elapsed = time.time() - start_time
        
        # 結果表示
        print(f"テスト実行時間: {elapsed:.2f}秒")
        
        # 標準出力と標準エラーを結合して検索
        combined_output = result.stdout + result.stderr
        
        print("出力:")
        print(combined_output)
        
        # 成功判定の修正 - OK/ok を探し、エラーや失敗がないかチェック
        success = (("OK" in combined_output or "ok" in combined_output) and 
                  "Traceback" not in combined_output and
                  "ModuleNotFoundError" not in combined_output and
                  "ImportError" not in combined_output and
                  "AssertionError" not in combined_output and
                  "FAILED" not in combined_output and
                  result.returncode == 0)
        print(f"テスト結果: {'成功' if success else '失敗'}")
        return success
        
    except subprocess.TimeoutExpired:
        print(f"テスト '{test_name}' がタイムアウトしました")
        return False
    except Exception as e:
        print(f"テスト実行中にエラーが発生しました: {e}")
        return False

def save_results(results):
    """テスト結果をJSONに保存"""
    with open(RESULT_FILE, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"テスト結果を {RESULT_FILE} に保存しました")

def main():
    """メイン実行関数"""
    print("E2E直接テストを開始します")
    
    # 実行するテスト
    tests = [
        "simplest_test",        # 最もシンプルなテスト
        "mini_test",            # 最小限のQtテスト
        "e2e_save_load",        # 保存読み込みテスト
        "e2e_basic_workflow",   # 基本的な操作フロー
        "e2e_resize_box"        # リサイズテスト
    ]
    
    # 結果
    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tests": {}
    }
    
    # 各テストを実行
    for test_name in tests:
        print(f"\n{'='*50}")
        print(f"テスト '{test_name}' を開始します")
        success = run_test_directly(test_name)
        results["tests"][test_name] = {
            "success": success,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        print(f"{'='*50}\n")
    
    # 結果をカウント
    success_count = sum(1 for test in results["tests"].values() if test["success"])
    results["summary"] = {
        "total": len(tests),
        "success": success_count,
        "failed": len(tests) - success_count
    }
    
    # 結果表示
    print("\nテスト実行結果サマリー:")
    print(f"合計: {results['summary']['total']}")
    print(f"成功: {results['summary']['success']}")
    print(f"失敗: {results['summary']['failed']}")
    
    # 結果保存
    save_results(results)
    
    return 0 if results["summary"]["failed"] == 0 else 1

if __name__ == "__main__":
    sys.exit(main()) 