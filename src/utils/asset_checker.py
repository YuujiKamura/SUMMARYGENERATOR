#!/usr/bin/env python3
"""
アプリケーションで必要な基本アセットの存在チェックと初期配置を行うモジュール
"""
import os
import shutil
import logging
from pathlib import Path
import requests
import yaml

# ロガー設定
logger = logging.getLogger(__name__)

class AssetChecker:
    """アセットの存在チェックと初期配置を行うクラス"""
    
    # 必要なディレクトリ構造
    REQUIRED_DIRS = [
        "yolo",
        "runs/train",
        "dataset/images/train",
        "dataset/images/val",
        "dataset/labels/train",
        "dataset/labels/val"
    ]
    
    # デフォルトのYOLOモデル（存在しない場合にダウンロード）
    DEFAULT_MODELS = {
        "yolov8n.pt": "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt",
        "yolov8s.pt": "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt"
    }
    
    # デフォルトのデータセット定義
    DEFAULT_DATASET_YAML = """
# YOLOv8 dataset config
path: dataset  # ワークスペースからの相対パス
train: images/train  # トレーニング画像の相対パス
val: images/val  # 検証画像の相対パス

# クラス定義
names:
  0: person
  1: bicycle
  2: car
"""
    
    def __init__(self, base_dir=None, verbose=True):
        """
        初期化
        
        Args:
            base_dir (str, optional): ベースディレクトリ、Noneならカレントディレクトリ
            verbose (bool): 詳細なログ出力を行うかどうか
        """
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.verbose = verbose
    
    def log(self, message, level=logging.INFO):
        """ログメッセージを出力"""
        if self.verbose:
            logger.log(level, message)
            print(message)  # ロガーが設定されていない場合のフォールバック
    
    def check_and_create_dirs(self):
        """必要なディレクトリ構造を確認し、存在しない場合は作成"""
        missing_dirs = []
        
        for dir_path in self.REQUIRED_DIRS:
            full_path = self.base_dir / dir_path
            if not full_path.exists():
                missing_dirs.append(dir_path)
                full_path.mkdir(parents=True, exist_ok=True)
                self.log(f"ディレクトリを作成しました: {full_path}")
        
        return missing_dirs
    
    def check_and_download_models(self):
        """基本的なYOLOモデルが存在するか確認し、なければダウンロード"""
        missing_models = []
        
        for model_name, model_url in self.DEFAULT_MODELS.items():
            model_path = self.base_dir / "yolo" / model_name
            if not model_path.exists():
                missing_models.append(model_name)
                self.log(f"モデル {model_name} をダウンロード中...")
                
                try:
                    # モデルをダウンロード
                    response = requests.get(model_url, stream=True)
                    response.raise_for_status()
                    
                    with open(model_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    self.log(f"モデル {model_name} のダウンロードが完了しました: {model_path}")
                
                except Exception as e:
                    self.log(f"モデル {model_name} のダウンロード中にエラーが発生しました: {e}", logging.ERROR)
        
        return missing_models
    
    def check_and_create_dataset_yaml(self):
        """データセット定義YAMLファイルを確認し、存在しなければ作成"""
        dataset_yaml_path = self.base_dir / "dataset" / "dataset.yaml"
        
        if not dataset_yaml_path.exists():
            # ディレクトリが存在することを確認
            dataset_yaml_path.parent.mkdir(parents=True, exist_ok=True)
            
            # YAMLファイルを作成
            with open(dataset_yaml_path, 'w', encoding='utf-8') as f:
                f.write(self.DEFAULT_DATASET_YAML.strip())
            
            self.log(f"デフォルトのデータセット定義ファイルを作成しました: {dataset_yaml_path}")
            return True
        
        return False
    
    def check_all_assets(self):
        """すべてのアセットをチェックし、不足しているものを初期配置"""
        self.log("アセットのチェックを開始します...")
        
        # ディレクトリ構造の確認と作成
        missing_dirs = self.check_and_create_dirs()
        if missing_dirs:
            self.log(f"作成したディレクトリ: {', '.join(missing_dirs)}")
        else:
            self.log("すべての必要なディレクトリが存在します")
        
        # モデルの確認とダウンロード
        missing_models = self.check_and_download_models()
        if missing_models:
            self.log(f"ダウンロードしたモデル: {', '.join(missing_models)}")
        else:
            self.log("すべての基本モデルが存在します")
        
        # データセット定義ファイルの確認と作成
        if self.check_and_create_dataset_yaml():
            self.log("デフォルトのデータセット定義を作成しました")
        else:
            self.log("データセット定義ファイルが存在します")
        
        self.log("アセットチェックが完了しました")
        return {
            "missing_dirs": missing_dirs,
            "missing_models": missing_models
        }

# コマンドラインから実行できるようにする
if __name__ == "__main__":
    import argparse
    
    # ロギングの設定
    # logging.basicConfig(
    #     level=logging.INFO,
    #     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    # )
    
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description='YOLOトレーニング＆予測マネージャーのアセットチェック')
    parser.add_argument('--base-dir', type=str, help='ベースディレクトリのパス（デフォルト：カレントディレクトリ）')
    parser.add_argument('--quiet', action='store_true', help='詳細なログ出力を抑制')
    
    args = parser.parse_args()
    
    # アセットチェックの実行
    checker = AssetChecker(base_dir=args.base_dir, verbose=not args.quiet)
    result = checker.check_all_assets()
    
    # 終了コードの設定
    exit_code = 0 if not (result["missing_dirs"] or result["missing_models"]) else 0
    exit(exit_code)