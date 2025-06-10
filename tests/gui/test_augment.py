#!/usr/bin/env python3
"""
データ拡張のGUIテスト
"""

"""テスト対象: src\yolo_train_predict_manager.py (エントリーポイント)"""
import os
import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QTextEdit, QPushButton, QLabel
from PyQt6.QtCore import QTimer

# プロジェクトルートをPython pathに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.data_augmenter import DataAugmentThread

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(800, 600)
        self.setWindowTitle('データ拡張テスト')
        
        # 中央ウィジェット
        self.central = QWidget()
        self.setCentralWidget(self.central)
        layout = QVBoxLayout(self.central)
        
        # 説明ラベル
        self.label = QLabel("このテストは学習データセットの拡張機能をテストします。")
        layout.addWidget(self.label)
        
        # コンソール
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        layout.addWidget(self.console)
        
        # ボタン
        self.btn = QPushButton('拡張開始')
        self.btn.clicked.connect(self.start_augment)
        layout.addWidget(self.btn)
        
        # スレッド
        self.thread = None
    
    def start_augment(self):
        # 拡張元のパスとデータ
        src_img_dir = 'dataset/images/train'
        src_label_dir = 'dataset/labels/train'
        dst_dir = 'dataset/augmented_gui_test'
        n_augment = 3
        
        self.console.append(f"拡張処理開始:")
        self.console.append(f"元画像: {src_img_dir}")
        self.console.append(f"元ラベル: {src_label_dir}")
        self.console.append(f"出力先: {dst_dir}")
        self.console.append(f"拡張数: {n_augment}個/画像")
        self.console.append("-------------------")
        
        # スレッド作成
        self.thread = DataAugmentThread(
            src_img_dir=src_img_dir, 
            src_label_dir=src_label_dir, 
            dst_dir=dst_dir, 
            n_augment=n_augment
        )
        
        # シグナル接続
        self.thread.output_received.connect(self.on_output)
        self.thread.process_finished.connect(self.on_finished)
        
        # スレッド開始
        self.thread.start()
        self.btn.setEnabled(False)
    
    def on_output(self, msg):
        # ログ出力を更新
        self.console.append(msg)
    
    def on_finished(self, code, result):
        # 処理完了
        self.console.append("========== 処理完了 ==========")
        self.console.append(f"終了コード: {code}")
        self.console.append(f"元画像数: {result.get('original_images', 0)}")
        self.console.append(f"拡張画像数: {result.get('augmented_images', 0)}")
        self.console.append(f"合計画像数: {result.get('total_images', 0)}")
        
        # ボタンを有効化
        self.btn.setEnabled(True)
        
        # 5秒後に閉じる
        QTimer.singleShot(5000, self.close)

def main():
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 