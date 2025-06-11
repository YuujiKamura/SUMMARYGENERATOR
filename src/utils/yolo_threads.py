#!/usr/bin/env python3
"""
YOLOモデルのトレーニングと予測を実行するスレッドクラスモジュール
"""
import torch
import ultralytics.nn.tasks
from torch.nn.modules.container import Sequential
# ultralytics.nn.modulesからConvなど必要なクラスをインポート
import ultralytics.nn.modules

# PyTorch 2.6以降のセキュリティ変更対応
try:
    # PyTorch 2.6+ かどうかを確認
    pytorch_version = torch.__version__.split('.')
    major, minor = int(pytorch_version[0]), int(pytorch_version[1])
    is_pytorch_26_plus = (major > 2) or (major == 2 and minor >= 6)
    
    if is_pytorch_26_plus:
        print(f"PyTorch {torch.__version__} 検出: セキュリティ対応が必要")
        
        # オリジナルのtorch.loadを保存
        original_torch_load = torch.load
        
        # モンキーパッチ - すべてのtorch.load呼び出しにweights_only=Falseを強制適用
        def patched_torch_load(f, **kwargs):
            # 明示的にweights_only=Falseを設定（モデルチェックポイントを完全ロード）
            kwargs['weights_only'] = False
            return original_torch_load(f, **kwargs)
        
        # グローバルなtorch.load関数を置き換え
        torch.load = patched_torch_load
        print("PyTorch 2.6+対応: torch.loadをパッチしました（weights_only=False）")
        
        # 念のためウルトラライティクスのクラスをホワイトリストに追加
        torch.serialization.add_safe_globals([
            ultralytics.nn.tasks.DetectionModel,
            torch.nn.modules.container.Sequential,
            ultralytics.nn.modules.Conv
        ])
        print("セーフグローバルクラスリストを設定しました")
    else:
        print(f"PyTorch {torch.__version__} は安全なモードを使用しません")
except Exception as e:
    print(f"PyTorch互換性設定中にエラー: {e}")

from PyQt6.QtCore import QThread, pyqtSignal
from ultralytics import YOLO
import os
import sys
import glob
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Union


class YoloPredictThread(QThread):
    """YOLO予測処理を別スレッドで実行するクラス"""
    # シグナル定義
    output_received = pyqtSignal(str)
    process_finished = pyqtSignal(int, dict)
    processing_file = pyqtSignal(str, int, int)
    detection_result = pyqtSignal(str, list)
    
    def __init__(self, model_path, image_dir, conf=0.25, output_dir="runs/predict", scan_subfolders=True):
        """
        初期化
        
        Args:
            model_path (str): YOLOモデルファイルのパス
            image_dir (str): 画像ディレクトリのパス
            conf (float): 信頼度閾値
            output_dir (str): 出力ディレクトリ
            scan_subfolders (bool): サブフォルダも探索するか
        """
        super().__init__()
        self.model_path = model_path
        self.image_dir = image_dir
        self.conf = conf
        self.output_dir = output_dir
        self.scan_subfolders = scan_subfolders
        self.running = True  # 停止フラグ
        
    def run(self):
        """スレッド実行処理 - ヘッドレスモードで実行"""
        try:
            # モデルを読み込む
            self.output_received.emit(f"モデル {self.model_path} を読み込み中...")
            model = YOLO(self.model_path)
            
            # 画像ファイルリストを取得
            if self.scan_subfolders:
                image_files = self._get_image_files_recursive()
            else:
                image_files = self._get_image_files()
                
            total_files = len(image_files)
            self.output_received.emit(f"{total_files}個の画像を処理します")
            
            # 結果格納用辞書
            results = {}
            
            # 各画像を処理
            for idx, image_file in enumerate(image_files, 1):
                if not self.running:
                    # 中断されたら2を返す
                    self.process_finished.emit(2, results)
                    return
                    
                # 現在処理中のファイルをGUIに通知
                self.processing_file.emit(image_file, idx, total_files)
                self.output_received.emit(f"予測中: {os.path.basename(image_file)}")
                
                # 画像を予測（verbose=Falseでヘッドレス実行、confでフィルタリング）
                predictions = model.predict(
                    source=image_file,
                    conf=self.conf,
                    save=False,  # 結果画像は保存しない (ヘッドレスモード)
                    project=self.output_dir,
                    verbose=False
                )
                
                if predictions and len(predictions) > 0:
                    # 検出結果を変換
                    detections = self._convert_predictions(predictions[0])
                    
                    # 結果を通知
                    self.detection_result.emit(image_file, detections)
                    
                    # 結果を保存
                    results[image_file] = detections
                else:
                    # 検出結果がない場合は空リストを設定
                    self.detection_result.emit(image_file, [])
                    results[image_file] = []
            
            # 処理完了
            self.output_received.emit("予測処理が完了しました")
            self.process_finished.emit(0, results)
            
        except Exception as e:
            error_msg = f"エラーが発生しました: {str(e)}"
            self.output_received.emit(error_msg)
            
            # エラー情報を辞書に格納
            error_dict = {
                "error": str(e),
                "traceback": sys.exc_info()[2].tb_frame.f_code.co_filename,
                "line": sys.exc_info()[2].tb_lineno
            }
            self.process_finished.emit(1, error_dict)
    
    def stop(self):
        """処理停止"""
        self.running = False
        self.output_received.emit("処理を停止しています...")
    
    def _get_image_files(self):
        """画像ファイルのリストを取得"""
        extensions = ["*.jpg", "*.jpeg", "*.png", "*.bmp", "*.gif"]
        files = []
        for ext in extensions:
            pattern = os.path.join(self.image_dir, ext)
            files.extend(glob.glob(pattern))
        return sorted(files)
    
    def _get_image_files_recursive(self):
        """サブフォルダを含む画像ファイルのリストを取得"""
        extensions = ["jpg", "jpeg", "png", "bmp", "gif"]
        files = []
        for ext in extensions:
            pattern = os.path.join(self.image_dir, f"**/*.{ext}")
            files.extend(glob.glob(pattern, recursive=True))
        return sorted(files)
    
    def _convert_predictions(self, prediction):
        """YOLOの予測結果をアプリの形式に変換"""
        detections = []
        
        # predictionからboxes, clsを取得
        if hasattr(prediction, 'boxes') and len(prediction.boxes) > 0:
            boxes = prediction.boxes
            
            # 各検出に対して
            for i in range(len(boxes)):
                # クラスIDとクラス名
                cls_id = int(boxes.cls[i])
                cls_name = prediction.names[cls_id] if cls_id in prediction.names else f"class_{cls_id}"
                
                # バウンディングボックス座標 (xmin, ymin, xmax, ymax)
                bbox = boxes.xyxy[i].tolist()
                
                # 信頼度
                conf = float(boxes.conf[i])
                
                # 検出結果を追加
                detection = {
                    "bbox": bbox,
                    "score": conf,
                    "label": cls_name
                }
                detections.append(detection)
        
        return detections


class YoloTrainThread(QThread):
    """YOLO.train() をバックグラウンドで走らせるスレッド"""
    output_received = pyqtSignal(str)
    process_finished = pyqtSignal(int, dict)  # 終了コードと結果辞書を送信
    
    def __init__(self, model_path, dataset_yaml, epochs, exp_name, project="runs/train", is_yolov11=False):
        """
        初期化
        
        Args:
            model_path (str): YOLOモデルファイルのパス
            dataset_yaml (str): データセット定義YAMLファイルのパス
            epochs (int): トレーニングエポック数
            exp_name (str): 実験名
            project (str): プロジェクトディレクトリ
            is_yolov11 (bool): YOLOv11モデルを使用するか
        """
        super().__init__()
        self.model_path = model_path
        self.dataset_yaml = dataset_yaml
        self.epochs = epochs
        self.exp_name = exp_name
        self.project = project
        self.is_yolov11 = is_yolov11
    
    def run(self):
        try:
            print("YoloTrainThread.run() 開始", flush=True)
            self.output_received.emit("トレーニングを開始します")
            # YOLOv11モデルの場合は特別な設定
            if self.is_yolov11:
                self.output_received.emit("YOLOv11モデルを使用します")
            # モデルを読み込む
            self.output_received.emit(f"モデル {self.model_path} を読み込み中...")
            model = YOLO(self.model_path)
            # デバイス自動判定
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.output_received.emit(f"使用デバイス: {device}")
            # データセット情報
            self.output_received.emit(f"データセット: {self.dataset_yaml}")
            # トレーニング実行
            self.output_received.emit("トレーニングを実行中...")
            results = model.train(
                data=self.dataset_yaml,
                epochs=self.epochs,
                name=self.exp_name,
                project=self.project,
                device=device
            )
            # 結果を取得
            metrics = results.results_dict
            best_fitness = metrics.get("metrics/precision(B)", 0)
            # 結果辞書を作成
            result_dict = {
                "best_model": os.path.join(self.project, self.exp_name, "weights", "best.pt"),
                "last_model": os.path.join(self.project, self.exp_name, "weights", "last.pt"),
                "results": {
                    "best_fitness": best_fitness,
                    "metrics": metrics
                }
            }
            # 完了メッセージ
            self.output_received.emit("トレーニングが完了しました")
            self.process_finished.emit(0, result_dict)
        except Exception as e:
            print(f"YoloTrainThread.run() 例外: {e}", flush=True)
            import traceback
            traceback.print_exc()
            # エラーメッセージを出力
            error_msg = f"エラーが発生しました: {str(e)}"
            self.output_received.emit(error_msg)
            # エラー情報を辞書に格納
            error_dict = {
                "error": str(e),
                "traceback": sys.exc_info()[2].tb_frame.f_code.co_filename,
                "line": sys.exc_info()[2].tb_lineno
            }
            self.process_finished.emit(1, error_dict)
    
    def stop(self):
        """トレーニングスレッドの停止（未実装ダミー）"""
        pass 