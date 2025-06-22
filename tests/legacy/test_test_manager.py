#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
テスト実行マネージャー自体をテストするスクリプト
"""
import os
import sys
import pytest
import logging
from pathlib import Path

# プロジェクトルートをPython pathに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

# テスト用ユーティリティをインポート
from tests.test_utils import setup_qt_test_environment, process_events

# PyQt6モジュールをインポート
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer, QProcess

# テスト実行マネージャーモジュールをインポート
from scripts.test_manager.main_window import MainWindow
from scripts.test_manager.test_manager import TestManager, TestResult

# ロガー設定
logger = logging.getLogger(__name__)

@pytest.mark.gui
@pytest.mark.integration
def test_test_manager_initialization(headless, qt_app):
    """テスト実行マネージャーの初期化テスト"""
    # テスト環境が準備できていることを確認
    assert qt_app is not None, "QApplicationが初期化されていません"
    
    try:
        # テスト実行マネージャーのメインウィンドウを作成
        logger.info("テスト実行マネージャーウィンドウを作成")
        window = MainWindow()
        
        # ウィンドウが正常に作成されたか確認
        assert window is not None
        assert window.manager is not None
        
        # 基本的なUI要素が正しく初期化されたか確認
        assert window.test_table is not None
        assert window.log_view is not None
        assert window.run_all_btn is not None
        assert window.run_selected_btn is not None
        assert window.stop_btn is not None
        
        # メインウィンドウを表示（ヘッドレスモードでは実際には表示されない）
        window.show()
        
        # イベントループを処理
        process_events(0.2)
        
        # メインウィンドウを閉じる
        window.close()
        
        logger.info("テスト実行マネージャー初期化テスト成功")
        
    except Exception as e:
        logger.error(f"テスト実行マネージャー初期化テストでエラー: {e}", exc_info=True)
        pytest.fail(f"テスト実行マネージャー初期化テスト失敗: {e}")

@pytest.mark.gui
@pytest.mark.integration
def test_test_manager_test_discovery(headless, qt_app):
    """テスト実行マネージャーのテスト検出機能テスト"""
    # テスト環境が準備できていることを確認
    assert qt_app is not None, "QApplicationが初期化されていません"
    
    try:
        # テスト実行マネージャーを作成
        logger.info("テスト実行マネージャーのテスト検出機能をテスト")
        manager = TestManager()
        
        # テスト検出シグナルを追跡するフラグ
        discovery_callback_called = False
        discovered_tests = []
        
        # コールバックを設定
        def on_tests_discovered(tests):
            nonlocal discovery_callback_called, discovered_tests
            discovery_callback_called = True
            discovered_tests = tests
            logger.info(f"{len(tests)}個のテストが検出されました")
        
        # シグナルを接続
        manager.test_discovered.connect(on_tests_discovered)
        
        # テスト検出を開始（強制更新）
        manager.discover_tests(force=True)
        
        # イベントループを処理（テスト検出は時間がかかる可能性がある）
        process_events(1.0)
        
        # コールバックが呼ばれたことを確認
        assert discovery_callback_called, "テスト検出コールバックが呼ばれませんでした"
        
        # テストが検出されたことを確認
        assert len(discovered_tests) > 0, "テストが検出されませんでした"
        
        # 特定のテストファイルが含まれていることを確認
        test_files = [test for test in discovered_tests if "test_" in test]
        assert len(test_files) > 0, "テストファイルが検出されませんでした"
        
        logger.info("テスト実行マネージャーのテスト検出テスト成功")
        
    except Exception as e:
        logger.error(f"テスト実行マネージャーのテスト検出テストでエラー: {e}", exc_info=True)
        pytest.fail(f"テスト実行マネージャーのテスト検出テスト失敗: {e}")

@pytest.mark.gui
@pytest.mark.integration
def test_test_manager_result_display(headless, qt_app):
    """テスト実行マネージャーの結果表示機能テスト"""
    # テスト環境が準備できていることを確認
    assert qt_app is not None, "QApplicationが初期化されていません"
    
    try:
        # テスト実行マネージャーのメインウィンドウを作成
        logger.info("テスト実行マネージャーの結果表示機能をテスト")
        window = MainWindow()
        window.show()
        
        # イベントループを処理
        process_events(0.2)
        
        # サンプルのテスト結果を作成
        test_result = TestResult(
            nodeid="tests/test_sample.py::test_function",
            status="passed",
            duration=0.123,
            last_run=None  # 現在時刻が自動的に使用される
        )
        
        # テスト結果のログを設定
        test_result.log = "=== テスト出力 ===\nこれはサンプルのテスト出力です\n=== テスト成功 ==="
        
        # テスト完了シグナルを手動で発行
        window._on_test_finished(
            test_result.nodeid, 
            test_result.status, 
            test_result.duration, 
            test_result.log
        )
        
        # イベントループを処理
        process_events(0.2)
        
        # ログビューにテスト結果が表示されたことを確認
        log_text = window.log_view.toPlainText()
        assert "tests/test_sample.py::test_function" in log_text, "テスト結果がログに表示されていません"
        assert "テスト出力" in log_text, "テスト出力がログに表示されていません"
        
        # テスト結果一覧にテスト結果が表示されたことを確認
        # 注: 実際のUIの場合、モデルを検索する必要がある
        
        # すべてのテストが完了したと見なすシグナルを発行
        window._on_all_tests_finished({test_result.nodeid: test_result})
        
        # イベントループを処理
        process_events(0.2)
        
        # ステータスバーに適切なメッセージが表示されているか確認
        status_text = window.statusBar().currentMessage()
        assert "テスト実行" in status_text, "ステータスバーに適切なメッセージが表示されていません"
        
        # ウィンドウを閉じる
        window.close()
        
        logger.info("テスト実行マネージャーの結果表示テスト成功")
        
    except Exception as e:
        logger.error(f"テスト実行マネージャーの結果表示テストでエラー: {e}", exc_info=True)
        pytest.fail(f"テスト実行マネージャーの結果表示テスト失敗: {e}")

@pytest.mark.gui
@pytest.mark.integration
def test_test_manager_error_handling(headless, qt_app):
    """テスト実行マネージャーのエラー処理テスト"""
    # テスト環境が準備できていることを確認
    assert qt_app is not None, "QApplicationが初期化されていません"
    
    try:
        # テスト実行マネージャーのメインウィンドウを作成
        logger.info("テスト実行マネージャーのエラー処理をテスト")
        window = MainWindow()
        window.show()
        
        # イベントループを処理
        process_events(0.2)
        
        # エラーステータスのテスト結果を作成
        error_result = TestResult(
            nodeid="tests/test_error.py::test_function",
            status="error",
            duration=0.1,
            last_run=None
        )
        
        # アクセス違反エラーのログを設定
        error_result.log = """=== 実行結果 ===
テスト実行クラッシュ (JSONレポートなし)
Windows fatal exception: access violation

Current thread 0x00002dfc (most recent call first):
  File "test.py", line 159 in function_call
  File "another.py", line 103 in another_function
"""
        
        # テスト完了シグナルを手動で発行
        window._on_test_finished(
            error_result.nodeid, 
            error_result.status, 
            error_result.duration, 
            error_result.log
        )
        
        # イベントループを処理
        process_events(0.2)
        
        # エラーがログに適切に表示されたことを確認
        log_text = window.log_view.toPlainText()
        assert "【エラー】" in log_text, "エラーマーカーがログに表示されていません"
        assert "スタックトレース" in log_text, "スタックトレースがログに表示されていません"
        assert "test.py, line 159 in function_call" in log_text or "File \"test.py\", line 159 in function_call" in log_text, "スタックトレースの中身が表示されていません"
        
        # 全テスト完了シグナルを発行
        window._on_all_tests_finished({error_result.nodeid: error_result})
        
        # イベントループを処理
        process_events(0.2)
        
        # ステータスバーにエラーメッセージが表示されているか確認
        status_text = window.statusBar().currentMessage()
        assert "エラー" in status_text or "失敗" in status_text, "ステータスバーにエラーメッセージが表示されていません"
        
        # ウィンドウを閉じる
        window.close()
        
        logger.info("テスト実行マネージャーのエラー処理テスト成功")
        
    except Exception as e:
        logger.error(f"テスト実行マネージャーのエラー処理テストでエラー: {e}", exc_info=True)
        pytest.fail(f"テスト実行マネージャーのエラー処理テスト失敗: {e}")

if __name__ == "__main__":
    # テスト環境をセットアップ
    setup_qt_test_environment()
    
    # テストを実行
    pytest.main(["-xvs", __file__]) 