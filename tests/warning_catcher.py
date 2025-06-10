#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
警告メッセージをキャプチャするためのスクリプト
"""

import sys
import os
import warnings
import io
import logging
import contextlib

def capture_warnings():
    """警告メッセージをキャプチャして表示する"""
    # 警告をキャプチャするための設定
    warning_stream = io.StringIO()
    warning_handler = logging.StreamHandler(warning_stream)
    warning_logger = logging.getLogger('py.warnings')
    warning_logger.addHandler(warning_handler)
    warning_logger.setLevel(logging.WARNING)
    
    # 警告を表示する設定
    warnings.resetwarnings()
    warnings.simplefilter('always')
    
    # 一時的にstderrをリダイレクト
    stderr_capture = io.StringIO()
    with contextlib.redirect_stderr(stderr_capture):
        # インポートと単純なテスト実行
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)
        
        # アプリケーションの終了
        if app:
            app.quit()
    
    # 警告内容を表示
    print("=== キャプチャした警告 ===")
    print(warning_stream.getvalue())
    print("=== 標準エラー出力 ===")
    print(stderr_capture.getvalue())
    print("========================")

if __name__ == "__main__":
    capture_warnings() 