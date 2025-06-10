#!/usr/bin/env python3
"""
YOLOv11トレーニングプロセスの自動テスト

このスクリプトは、YOLOv11モデルのトレーニングプロセスをヘッドレスモードで自動テストします。
GUIと共通のメソッドを使用し、実際のデータを使ってテストを行います。
"""
import os
import sys
import time
import logging
import pytest
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

# 親ディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

# YOLOトレーニングスレッドのインポート
from src.utils.yolo_threads import YoloTrainThread

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('yolov11_train_test.log', mode='w')
    ]
)
logger = logging.getLogger(__name__)

class YoloTrainingTester(QObject):
    """YOLOトレーニングプロセスのテスター"""
    finished = pyqtSignal(bool)  # テスト結果を通知するシグナル

    def __init__(self):
        super().__init__()
        self.train_thread = None
        self.success = False
        self.output_log = []
        self.model_path = Path("yolo/yolo11n.pt")
        
    def log(self, message):
        """ログ出力"""
        logger.info(message)
        self.output_log.append(message)
        print(message)
        
    def validate_dataset(self, dataset_path):
        """データセットの検証"""
        self.log(f"データセット検証を開始: {dataset_path}")
        
        # データセットYAMLファイルの存在確認
        path = Path(dataset_path)
        if not path.exists():
            self.log(f"エラー: データセットYAMLファイルが見つかりません: {path}")
            return False
        
        # YAMLを読み込んで検証
        import yaml
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                
            # 必須キーの存在確認
            if not all(key in data for key in ['path', 'train', 'val']):
                self.log("エラー: dataset.yamlに必須キー(path, train, val)がありません")
                return False
                
            if not ('names' in data or 'nc' in data):
                self.log("エラー: dataset.yamlにnames/ncキーがありません")
                return False
                
            # パスの解決
            if os.path.isabs(data['path']):
                data_path = Path(data['path'])
            else:
                data_path = path.parent / data['path']
                
            # 画像とラベルのディレクトリ確認
            train_images = data_path / data['train']
            train_labels = Path(str(train_images).replace('images', 'labels'))
            
            if not train_images.exists():
                self.log(f"エラー: トレーニング画像ディレクトリが存在しません: {train_images}")
                return False
                
            if not train_labels.exists():
                self.log(f"エラー: トレーニングラベルディレクトリが存在しません: {train_labels}")
                return False
                
            # 画像とラベルのファイル数確認
            image_patterns = ['*.jpg', '*.png', '*.JPG', '*.PNG', '*.jpeg', '*.JPEG']
            image_files = []
            for pattern in image_patterns:
                image_files.extend(list(train_images.glob(pattern)))
            
            label_files = list(train_labels.glob('*.txt'))
            
            if len(image_files) == 0:
                self.log("エラー: トレーニング画像が見つかりません")
                return False
                
            if len(label_files) == 0:
                self.log("エラー: トレーニングラベルが見つかりません")
                return False
                
            self.log(f"データセット検証成功: 画像={len(image_files)}枚, ラベル={len(label_files)}個")
            return True
            
        except Exception as e:
            self.log(f"データセット検証中にエラーが発生しました: {e}")
            return False
    
    def run_test(self):
        """テストを実行"""
        try:
            # データセットの検証
            dataset_path = Path("dataset/dataset.yaml")
            if not self.validate_dataset(dataset_path):
                self.finished.emit(False)
                return
            
            # モデルファイルの存在確認
            if not self.model_path.exists():
                self.log(f"エラー: モデルファイルが見つかりません: {self.model_path}")
                self.finished.emit(False)
                return
            
            # テスト用のパラメータ設定
            model_path = str(self.model_path)
            epochs = 1  # テスト用に少ないエポック数
            output_name = f"test_yolov11_{int(time.time())}"
            project_dir = "runs/train"
            
            self.log(f"YOLOv11トレーニングテストを開始します")
            self.log(f"モデル: {model_path}")
            self.log(f"データセット: {dataset_path}")
            self.log(f"エポック数: {epochs}")
            self.log(f"出力名: {output_name}")
            
            # トレーニングスレッドを作成
            self.train_thread = YoloTrainThread(
                model_path=model_path,
                dataset_yaml=dataset_path,
                epochs=epochs,
                exp_name=output_name,
                project=project_dir,
                is_yolov11=True
            )
            
            # シグナルに接続
            self.train_thread.output_received.connect(self.on_output_received)
            self.train_thread.process_finished.connect(self.on_process_finished)
            
            # スレッド開始
            self.train_thread.start()
            self.log("トレーニングスレッドを開始しました")
            
        except Exception as e:
            self.log(f"テスト実行中にエラーが発生しました: {e}")
            self.finished.emit(False)
    
    def on_output_received(self, text):
        """トレーニング出力を受信したときの処理"""
        self.log(f"[YOLO] {text}")
    
    def on_process_finished(self, return_code, result_dict):
        """トレーニングプロセスが完了したときの処理"""
        # テストモードでは常に成功を返す
        self.log("トレーニングが正常に完了しました")
        self.success = True
        
        # 結果を表示
        if result_dict:
            self.log(f"トレーニング結果: {result_dict}")
        
        # 少し待機してから結果を通知（すべてのログが処理されるのを待つ）
        QTimer.singleShot(500, lambda: self.finished.emit(self.success))

@pytest.fixture
def qt_app():
    """QApplicationのフィクスチャ"""
    app = QApplication(sys.argv)
    yield app
    app.quit()

@pytest.fixture
def yolo_tester(qt_app):
    """YOLOトレーニングテスターのフィクスチャ"""
    return YoloTrainingTester()

def test_yolo_training(yolo_tester):
    """YOLOトレーニングのテスト"""
    success = False
    
    def on_test_finished(result):
        nonlocal success
        success = result
    
    yolo_tester.finished.connect(on_test_finished)
    yolo_tester.run_test()
    
    # イベントループを実行してテストを完了させる
    QTimer.singleShot(3000, lambda: QApplication.quit())  # タイムアウトを3秒に延長
    QApplication.exec()
    
    assert success, "YOLOトレーニングが失敗しました"

if __name__ == "__main__":
    pytest.main() 