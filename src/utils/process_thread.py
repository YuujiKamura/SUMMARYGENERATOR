#!/usr/bin/env python3
"""
外部コマンドの実行を行うスレッドクラスモジュール
"""
import subprocess
import sys
import locale
from PyQt6.QtCore import QThread, pyqtSignal

class ProcessThread(QThread):
    """コマンド実行用のスレッド"""
    output_received = pyqtSignal(str)
    process_finished = pyqtSignal(int)
    
    def __init__(self, command):
        super().__init__()
        self.command = command
        
    def run(self):
        """スレッドのメイン処理"""
        # システムのデフォルトエンコーディングを取得
        try:
            # Windows環境ではcp932などになることがある
            system_encoding = locale.getpreferredencoding()
            
            # Windows環境では特に日本語環境でutf-8を強制する
            if sys.platform.startswith('win'):
                encoding = 'utf-8'
            else:
                encoding = system_encoding
        except:
            # フォールバック
            encoding = 'utf-8'
        
        try:
            process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding=encoding,
                errors='replace',  # 不明な文字はU+FFFD () に置換
                shell=True
            )
            
            # リアルタイムで出力を取得
            for line in iter(process.stdout.readline, ''):
                self.output_received.emit(line.strip())
                
            process.stdout.close()
            return_code = process.wait()
            self.process_finished.emit(return_code)
            
        except Exception as e:
            self.output_received.emit(f"プロセス実行中にエラーが発生しました: {str(e)}")
            self.process_finished.emit(1)  # エラーコード 