#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
テスト実行環境に関するヘルパー関数
"""

import os
import sys
import inspect
import platform
import pytest

@pytest.mark.unit
def is_test_manager_gui():
    """
    テストマネージャーGUI環境で実行中かどうかを検出
    
    Returns:
        bool: テストマネージャGUIならTrue
    """
    # 環境変数や実行コマンドからテストマネージャGUIを検出
    if 'PYTEST_CURRENT_TEST' in os.environ:
        return True
        
    # スタックトレースを調べて呼び出し元がテストマネージャかチェック
    for frame in inspect.stack():
        if 'pytest' in frame.filename or 'pytest_runner' in frame.filename:
            return True
            
    # コマンドライン引数を確認
    return any('pytest' in arg for arg in sys.argv)


@pytest.mark.unit
def is_windows():
    """Windowsプラットフォームかどうかを検出"""
    return platform.system() == 'Windows'


@pytest.mark.unit
def setup_platform_environment():
    """実行プラットフォームに合わせた設定"""
    if is_windows():
        # Windowsでのテスト実行時の特殊設定
        os.environ['QT_SCALE_FACTOR'] = '1'
        return "Windows環境設定完了"
    elif platform.system() == 'Linux':
        # Linuxでの設定
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        return "Linux環境設定完了"
    return f"{platform.system()}環境設定完了"


@pytest.mark.unit
def headless_test_mode():
    """ヘッドレステストモードを強制的に有効化"""
    # ヘッドレスモードの環境変数を設定
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["QT_LOGGING_TO_CONSOLE"] = "0"
    os.environ["QT_FORCE_HEADLESS"] = "1"
    
    # テストマネージャGUIの検出
    is_gui = is_test_manager_gui()
    
    # プラットフォーム固有の設定
    setup_platform_environment()
    
    return is_gui 