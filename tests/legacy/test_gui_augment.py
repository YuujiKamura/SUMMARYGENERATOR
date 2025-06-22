#!/usr/bin/env python3
"""
データ拡張タブのクリック自動テスト
"""
import sys
import os
import time
from pathlib import Path

# アプリケーションのソースディレクトリをPYTHONPATHに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, QPoint, Qt, QEvent
from PyQt6.QtTest import QTest

# ここではパスが設定されているのでimportできる
from src.yolo_train_predict_manager import YoloTrainPredictManager

class GUITester:
    """GUIの自動テスト"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.window = YoloTrainPredictManager()
        self.window.show()
        
        # テストのステップ
        self.steps = [
            self.switch_to_augment_tab,
            self.setup_paths,
            self.start_augmentation,
            self.wait_for_completion,
            self.exit_app
        ]
        self.current_step = 0
        
        # テストの実行
        QTimer.singleShot(500, self.execute_next_step)
        
    def execute_next_step(self):
        """次のテストステップを実行"""
        if self.current_step < len(self.steps):
            print(f"ステップ {self.current_step+1}: {self.steps[self.current_step].__name__}")
            self.steps[self.current_step]()
            self.current_step += 1
        else:
            print("テスト完了")
            self.app.quit()
    
    def switch_to_augment_tab(self):
        """データ拡張タブに切り替え"""
        self.window.tabs.setCurrentIndex(4)  # データ拡張タブはインデックス4
        print("データ拡張タブに切り替えました")
        QTimer.singleShot(500, self.execute_next_step)
    
    def setup_paths(self):
        """パス設定"""
        # 画像フォルダとラベルフォルダの設定
        self.window.augment_src_img_edit.setText('dataset/images/train')
        self.window.augment_src_label_edit.setText('dataset/labels/train')
        self.window.augment_dst_dir_edit.setText('dataset/augmented_gui_auto_test')
        self.window.augment_count_spin.setValue(3)
        
        print("拡張設定を入力しました:")
        print(f"  - 元画像フォルダ: {self.window.augment_src_img_edit.text()}")
        print(f"  - 元ラベルフォルダ: {self.window.augment_src_label_edit.text()}")
        print(f"  - 出力先フォルダ: {self.window.augment_dst_dir_edit.text()}")
        print(f"  - 拡張数: {self.window.augment_count_spin.value()}")
        
        QTimer.singleShot(500, self.execute_next_step)
    
    def start_augmentation(self):
        """拡張開始ボタンをクリック"""
        print("拡張開始ボタンをクリックします")
        QTest.mouseClick(self.window.augment_btn, Qt.MouseButton.LeftButton)
        
        # 拡張開始したことを検証
        if not self.window.augment_btn.isEnabled():
            print("✓ 拡張処理が開始されました（ボタンが無効化されました）")
        else:
            print("× 拡張処理が開始されませんでした")
        
        QTimer.singleShot(1000, self.execute_next_step)
    
    def wait_for_completion(self):
        """処理完了を待機"""
        if self.window.augment_thread and self.window.augment_thread.isRunning():
            print("拡張処理実行中... (30秒後に確認)")
            QTimer.singleShot(30000, self.check_completion)
        else:
            print("× スレッドが起動していません")
            self.execute_next_step()
    
    def check_completion(self):
        """完了したかチェック"""
        if self.window.augment_btn.isEnabled():
            print("✓ 拡張処理が完了しました")
        else:
            print("× 拡張処理がまだ完了していません")
        
        output_dir = Path('dataset/augmented_gui_auto_test')
        if output_dir.exists() and (output_dir / 'dataset.yaml').exists():
            print(f"✓ 出力ディレクトリが作成されました: {output_dir}")
            image_count = len(list((output_dir / 'images').glob('*')))
            print(f"  - 画像ファイル数: {image_count}")
        else:
            print(f"× 出力ディレクトリが作成されていません: {output_dir}")
        
        self.execute_next_step()
    
    def exit_app(self):
        """アプリケーションを終了"""
        print("テスト完了、アプリケーションを終了します")
        self.window.close()
        self.app.quit()

if __name__ == "__main__":
    tester = GUITester()
    sys.exit(tester.app.exec()) 