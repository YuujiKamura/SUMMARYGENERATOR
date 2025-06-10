#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import unittest
import logging

# ロギング設定
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("run_single_test")

if __name__ == "__main__":
    # 実行するテストを指定
    if len(sys.argv) < 3:
        print("使用方法: python run_single_test.py <テストファイル> <テストメソッド>")
        print("例: python run_single_test.py e2e_test TestPhotoCategorizerE2E.test_e2e_save_load_cycle")
        sys.exit(1)
    
    test_file = sys.argv[1]
    test_method = sys.argv[2]
    
    logger.info(f"テストファイル '{test_file}' からテスト '{test_method}' を実行します")
    
    try:
        # テストをロード
        loader = unittest.TestLoader()
        
        # テストファイルをインポート
        __import__(f"tests.{test_file}")
        module = sys.modules[f"tests.{test_file}"]
        
        if "." in test_method:
            class_name, method_name = test_method.split(".")
            test_suite = loader.loadTestsFromName(f"{method_name}", getattr(module, class_name))
        else:
            test_suite = loader.loadTestsFromName(test_method, module)
        
        # テストを実行
        runner = unittest.TextTestRunner(verbosity=2)
        
        # タイムアウトを設定（ここではシグナルで実装する代わりに手動で設定）
        import threading
        
        def timeout_handler():
            logger.error("テストがタイムアウトしました。強制終了します。")
            import os
            os._exit(1)
        
        # タイムアウトタイマーを設定（30秒）
        timer = threading.Timer(30.0, timeout_handler)
        timer.start()
        
        # テストを実行
        result = runner.run(test_suite)
        
        # タイマーをキャンセル
        timer.cancel()
        
        # 結果の表示
        if result.wasSuccessful():
            logger.info("テストは正常に完了しました")
            sys.exit(0)
        else:
            logger.error("テストに失敗しました")
            sys.exit(1)
    
    except Exception as e:
        logger.error(f"テスト実行中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 