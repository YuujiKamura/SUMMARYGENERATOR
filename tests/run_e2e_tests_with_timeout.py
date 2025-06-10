#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import unittest
import logging
import time
import threading
import traceback
import os

# ロギング設定
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("run_e2e_tests")

# テストタイムアウト（秒）
TEST_TIMEOUT = 10

# インポート
try:
    from e2e_test import TestPhotoCategorizerE2E
    tests_available = True
except ImportError as e:
    logger.error(f"テストモジュールをインポートできません: {e}")
    tests_available = False

def run_test_with_timeout(test_case, test_method_name):
    """タイムアウト付きでテストを実行"""
    logger.info(f"テスト {test_method_name} を実行します（タイムアウト: {TEST_TIMEOUT}秒）")
    
    # テストメソッドを取得
    test_method = getattr(test_case, test_method_name)
    
    # 結果格納用
    results = {"success": False, "error": None}
    
    # テスト実行スレッド
    def test_thread():
        try:
            # テスト前の準備
            test_case.setUp()
            
            # テストを実行
            test_method()
            
            # 後片付け
            test_case.tearDown()
            
            # 正常終了
            results["success"] = True
        except Exception as e:
            results["error"] = e
            logger.error(f"テスト実行中にエラーが発生しました: {e}")
            traceback.print_exc()
    
    # テストスレッドを開始
    thread = threading.Thread(target=test_thread)
    thread.daemon = True
    start_time = time.time()
    thread.start()
    
    # タイムアウトを待つ
    thread.join(TEST_TIMEOUT)
    
    # タイムアウトしたかチェック
    if thread.is_alive():
        logger.error(f"テスト {test_method_name} がタイムアウトしました（{TEST_TIMEOUT}秒）")
        return False, f"テストがタイムアウトしました（{TEST_TIMEOUT}秒）"
    
    elapsed = time.time() - start_time
    logger.info(f"テスト {test_method_name} が完了しました（所要時間: {elapsed:.2f}秒）")
    
    if results["success"]:
        return True, None
    else:
        return False, results["error"]

def main():
    """メイン実行関数"""
    if not tests_available:
        logger.error("必要なテストモジュールが利用できないため、終了します")
        return 1
    
    logger.info("E2Eテストを開始します（タイムアウト付き）")
    
    # テストケースを初期化
    test_case = TestPhotoCategorizerE2E()
    
    # クラスセットアップを実行
    try:
        TestPhotoCategorizerE2E.setUpClass()
    except Exception as e:
        logger.error(f"クラスセットアップでエラーが発生しました: {e}")
        traceback.print_exc()
        return 1
    
    # テストメソッド一覧
    test_methods = [
        "test_e2e_basic_workflow",
        "test_e2e_resize_bounding_box",
        "test_e2e_save_load_cycle"
    ]
    
    # 結果カウンター
    results = {
        "success": 0,
        "failed": 0,
        "total": len(test_methods)
    }
    
    # 各テストを実行
    for method_name in test_methods:
        logger.info(f"テスト {method_name} を開始します")
        
        success, error = run_test_with_timeout(test_case, method_name)
        
        if success:
            results["success"] += 1
            logger.info(f"テスト {method_name} は成功しました")
        else:
            results["failed"] += 1
            logger.error(f"テスト {method_name} は失敗しました: {error}")
    
    # クラスの終了処理
    try:
        TestPhotoCategorizerE2E.tearDownClass()
    except Exception as e:
        logger.error(f"クラスの終了処理でエラーが発生しました: {e}")
        traceback.print_exc()
    
    # 結果を表示
    logger.info(f"テスト実行完了: 合計 {results['total']}、成功 {results['success']}、失敗 {results['failed']}")
    
    return 0 if results["failed"] == 0 else 1

if __name__ == "__main__":
    sys.exit(main()) 