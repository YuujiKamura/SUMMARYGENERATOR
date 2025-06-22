#!/usr/bin/env python3
"""
YOLOトレーニングスレッドとYOLO予測スレッドのユニットテスト
"""

"""テスト対象: src\utils\yolo_threads.py (バックエンドモジュール)"""
import sys
import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# テスト対象のモジュールのパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent))

# テスト対象のモジュールをインポート
try:
    from src.utils.yolo_threads import YoloTrainThread, YoloPredictThread
except ImportError:
    from utils.yolo_threads import YoloTrainThread, YoloPredictThread

@pytest.mark.yolo
@pytest.mark.integration
class TestYoloTrainThread(unittest.TestCase):
    """YoloTrainThreadのユニットテスト"""
    
    @pytest.mark.yolo
    @pytest.mark.integration
    def setUp(self):
        """各テストケースのセットアップ"""
        self.model_path = "yolo/yolov8n.pt"
        self.dataset_yaml = "dataset/dataset.yaml"
        self.epochs = 100
        self.exp_name = "test_exp"
        self.is_yolov11 = False
        
        # トレーニング結果のモック
        self.mock_results = MagicMock()
        self.mock_results.results_dict = {
            "metrics/precision(B)": 0.85,
            "metrics/recall(B)": 0.80,
            "metrics/mAP50(B)": 0.82,
            "metrics/mAP50-95(B)": 0.75
        }
    
    @pytest.mark.yolo
    @pytest.mark.integration
    def test_train_thread_initialization(self):
        """トレーニングスレッドの初期化テスト"""
        # スレッドインスタンスを作成
        thread = YoloTrainThread(
            model_path=self.model_path,
            dataset_yaml=self.dataset_yaml,
            epochs=self.epochs,
            exp_name=self.exp_name
        )
        
        # パラメータが正しく設定されているか確認
        self.assertEqual(thread.model_path, self.model_path)
        self.assertEqual(thread.dataset_yaml, self.dataset_yaml)
        self.assertEqual(thread.epochs, self.epochs)
        self.assertEqual(thread.exp_name, self.exp_name)
    
    @pytest.mark.yolo
    @pytest.mark.integration
    @patch('ultralytics.YOLO')
    def test_train_command_generation(self, mock_yolo):
        """トレーニングコマンド生成のテスト"""
        # YOLOインスタンスのモック設定
        mock_yolo_instance = MagicMock()
        mock_yolo_instance.train.return_value = self.mock_results
        mock_yolo.return_value = mock_yolo_instance
        
        # シグナル受信用のモック
        output_received = MagicMock()
        process_finished = MagicMock()
        
        # スレッドインスタンスを作成
        thread = YoloTrainThread(
            model_path=self.model_path,
            dataset_yaml=self.dataset_yaml,
            epochs=self.epochs,
            exp_name=self.exp_name
        )
        
        # シグナルに接続
        thread.output_received.connect(output_received)
        thread.process_finished.connect(process_finished)
        
        # run()メソッドを呼び出す
        thread.run()
        
        # 出力シグナルが発行されたことを確認
        assert output_received.call_count >= 5  # 少なくとも5回の出力
        output_messages = [args[0][0] for args in output_received.call_args_list]
        assert any("トレーニングを開始します" in msg for msg in output_messages)
        assert any("トレーニングが完了しました" in msg for msg in output_messages)
        
        # プロセス終了シグナルが成功コード（0）で呼ばれたことを確認
        process_finished.assert_called_once()
        args = process_finished.call_args[0]
        assert args[0] == 0  # 終了コード
        assert isinstance(args[1], dict)  # 結果辞書
        assert "best_model" in args[1]
        assert "last_model" in args[1]
        assert "results" in args[1]
        assert args[1]["results"]["best_fitness"] == 0.85
    
    @pytest.mark.yolo
    @pytest.mark.integration
    @patch('ultralytics.YOLO')
    def test_yolov11_train_command(self, mock_yolo):
        """YOLOv11トレーニングコマンド生成のテスト"""
        # YOLOインスタンスのモック設定
        mock_yolo_instance = MagicMock()
        mock_yolo_instance.train.return_value = self.mock_results
        mock_yolo.return_value = mock_yolo_instance
        
        # シグナル受信用のモック
        output_received = MagicMock()
        process_finished = MagicMock()
        
        # YOLOv11用スレッドインスタンスを作成
        thread = YoloTrainThread(
            model_path="yolo/yolo11n.pt",
            dataset_yaml=self.dataset_yaml,
            epochs=self.epochs,
            exp_name=self.exp_name,
            is_yolov11=True
        )
        
        # シグナルに接続
        thread.output_received.connect(output_received)
        thread.process_finished.connect(process_finished)
        
        # run()メソッドを呼び出す
        thread.run()
        
        # 出力シグナルが発行されたことを確認
        assert output_received.call_count >= 5  # 少なくとも5回の出力
        output_messages = [args[0][0] for args in output_received.call_args_list]
        assert any("トレーニングを開始します" in msg for msg in output_messages)
        assert any("YOLOv11モデルを使用します" in msg for msg in output_messages)
        assert any("トレーニングが完了しました" in msg for msg in output_messages)
        
        # プロセス終了シグナルが成功コード（0）で呼ばれたことを確認
        process_finished.assert_called_once()
        args = process_finished.call_args[0]
        assert args[0] == 0  # 終了コード
        assert isinstance(args[1], dict)  # 結果辞書
        assert "best_model" in args[1]
        assert "last_model" in args[1]
        assert "results" in args[1]
        assert args[1]["results"]["best_fitness"] == 0.85

@pytest.mark.yolo
@pytest.mark.integration
class TestYoloPredictThread(unittest.TestCase):
    """YoloPredictThreadのユニットテスト"""
    
    @pytest.mark.yolo
    @pytest.mark.integration
    def setUp(self):
        """各テストケースのセットアップ"""
        self.model_path = "yolo/yolov8n.pt"
        self.image_dir = "dataset/images/val"
        self.output_dir = "runs/predict/test_predict"
        self.conf = 0.25
        
        # 予測結果のモック
        self.mock_result = MagicMock()
        self.mock_result.path = "test_image.jpg"
        self.mock_result.boxes = MagicMock()
        self.mock_result.boxes.xyxy = [[100, 100, 200, 200]]
        self.mock_result.boxes.conf = [0.95]
        self.mock_result.boxes.cls = [0]
        self.mock_result.names = {0: "管理図ボード"}
    
    @pytest.mark.yolo
    @pytest.mark.integration
    def test_predict_thread_initialization(self):
        """予測スレッドの初期化テスト"""
        # スレッドインスタンスを作成
        thread = YoloPredictThread(
            model_path=self.model_path,
            image_dir=self.image_dir,
            output_dir=self.output_dir,
            conf=self.conf
        )
        
        # パラメータが正しく設定されているか確認
        self.assertEqual(thread.model_path, self.model_path)
        self.assertEqual(thread.image_dir, self.image_dir)
        self.assertEqual(thread.output_dir, self.output_dir)
        self.assertEqual(thread.conf, self.conf)
    
    @pytest.mark.yolo
    @pytest.mark.integration
    @patch('ultralytics.YOLO')
    @patch('glob.glob')
    def test_predict_command_generation(self, mock_glob, mock_yolo):
        """予測コマンド生成のテスト"""
        # モックを設定
        mock_glob.side_effect = [
            ["test_image.jpg"],  # *.jpg
            [],  # *.jpeg
            [],  # *.png
            [],  # *.bmp
            []   # *.gif
        ]
        
        # YOLOインスタンスのモック設定
        mock_yolo_instance = MagicMock()
        mock_yolo_instance.predict.return_value = [self.mock_result]
        mock_yolo.return_value = mock_yolo_instance
        
        # シグナル受信用のモック
        output_received = MagicMock()
        process_finished = MagicMock()
        processing_file = MagicMock()
        detection_result = MagicMock()
        
        # スレッドインスタンスを作成
        thread = YoloPredictThread(
            model_path=self.model_path,
            image_dir=self.image_dir,
            output_dir=self.output_dir,
            conf=self.conf
        )
        
        # シグナルに接続
        thread.output_received.connect(output_received)
        thread.process_finished.connect(process_finished)
        thread.processing_file.connect(processing_file)
        thread.detection_result.connect(detection_result)
        
        # run()メソッドを呼び出す
        thread.run()
        
        # YOLOインスタンスが作成されたことを確認
        mock_yolo.assert_called_once_with(self.model_path)
        
        # YOLO.predictメソッドが呼び出されたか確認
        mock_yolo_instance.predict.assert_called_once()
        
        # 呼び出し時のパラメータを確認
        args = mock_yolo_instance.predict.call_args[1]
        self.assertEqual(args["conf"], self.conf)
        self.assertEqual(args["save"], False)  # ヘッドレスモードでは保存しない
        self.assertEqual(args["project"], self.output_dir)
        self.assertTrue(args["verbose"] is False)  # ヘッドレスモード
        
        # シグナルが正しく発行されたか確認
        assert output_received.call_count >= 2  # 少なくとも2回の出力
        assert process_finished.call_count == 1  # 終了シグナル
        assert processing_file.call_count == 1  # ファイル処理シグナル
        assert detection_result.call_count == 1  # 検出結果シグナル
        
        # 検出結果の内容を確認
        detection_args = detection_result.call_args[0]
        assert detection_args[0] == "test_image.jpg"  # 画像パス
        assert len(detection_args[1]) == 1  # 検出結果の数
        assert detection_args[1][0]["bbox"] == [100, 100, 200, 200]  # バウンディングボックス
        assert detection_args[1][0]["score"] == 0.95  # 信頼度
        assert detection_args[1][0]["label"] == "管理図ボード"  # ラベル


if __name__ == "__main__":
    unittest.main() 