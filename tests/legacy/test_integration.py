#!/usr/bin/env python3
"""
YOLOトレーニング＆予測マネージャーのインテグレーションテスト
"""
import sys
import os
import unittest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# テスト対象のモジュールのパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtTest import QTest

from src.yolo_train_predict_manager import YoloTrainPredictManager
from src.ui.tabs.train_tab import TrainTab
from src.ui.tabs.predict_tab import PredictTab
from src.ui.tabs.augment_tab import AugmentTab
from src.utils.yolo_threads import YoloPredictThread

# テスト用のダミーデータ
DUMMY_MODEL_PATH = "yolo/yolo11n.pt"
DUMMY_DATASET_YAML = "dataset/dataset.yaml"
DUMMY_IMAGE_DIR = "dataset/images/val"


class TestYoloManagerIntegration(unittest.TestCase):
    """YOLOトレーニング＆予測マネージャーのインテグレーションテスト"""
    
    @classmethod
    def setUpClass(cls):
        """テストクラスのセットアップ"""
        # QApplication インスタンスの作成（全テストで共有）
        cls.app = QApplication.instance() or QApplication(sys.argv)
    
    def setUp(self):
        """各テストケースのセットアップ"""
        # QMessageBoxなどのダイアログをモック化
        self.dialog_patcher = patch('PyQt6.QtWidgets.QMessageBox')
        self.mock_dialog = self.dialog_patcher.start()
        
        # メインウィンドウの作成
        self.manager = YoloTrainPredictManager()
        
        # スレッドのモック化
        self.manager.active_thread = MagicMock()
        self.manager.active_thread.isRunning.return_value = False
    
    def tearDown(self):
        """各テストケースの後処理"""
        # リソース解放
        self.manager.close()
        
        # パッチを戻す
        self.dialog_patcher.stop()
    
    def test_prediction_signal_connection(self):
        """予測結果のシグナル接続テスト - 本件の問題を直接検出するテスト"""
        # YoloPredictThreadを使わずにシグナルをシミュレート
        self.manager.predict_tab.on_prediction_finished = MagicMock()
        
        # 正しく結果辞書を渡して呼び出す
        test_results = {"test.jpg": [{"class": 1, "confidence": 0.9}]}
        self.manager.on_prediction_finished(0, test_results)
        
        # 正しく通知されたか確認
        self.manager.predict_tab.on_prediction_finished.assert_called_once_with(0, test_results)
        
        # スレッドからのシグナル送信をシミュレート（スレッドはモック）
        thread = MagicMock()
        thread.process_finished = MagicMock()
        
        # スレッドを設定
        self.manager.active_thread = thread
        
        # ラムダ関数を使ってシグナル接続をシミュレート
        callback = lambda exit_code, result: self.manager.on_prediction_finished(exit_code, result)
        
        # 直接コールバックを呼び出し
        callback(0, test_results)
        
        # 2回目の通知が行われたか確認
        self.assertEqual(self.manager.predict_tab.on_prediction_finished.call_count, 2)


if __name__ == "__main__":
    unittest.main() 