#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OCR処理のヘッドレステスト
詳細なデバッグログを出力しながら実行する
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path

# プロジェクトルートをパスに追加
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

# ロギング設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # コンソールに出力
        logging.FileHandler('ocr_test_debug.log', encoding='utf-8')  # ファイルにも出力
    ]
)

logger = logging.getLogger('ocr_test')

# モックデータ用の画像ディレクトリ
test_img_dir = os.path.join(current_dir, "data", "dataset_photos")

# 必要なインポート
from app.controllers.settings_manager import SettingsManager
from app.controllers.model_manager import ModelManager
from app.controllers.ocr_controller import OcrController
from app.utils.paths import OCR_CACHE_FILE, DETECTION_RESULTS_FILE, DATA_DIR
from app.utils.config_loader import load_config


def list_image_files(directory):
    """ディレクトリ内の画像ファイルをリストアップ"""
    if not os.path.exists(directory):
        logger.error(f"ディレクトリが存在しません: {directory}")
        return []
    
    logger.info(f"ディレクトリをスキャン中: {directory}")
    image_files = []
    extensions = (".jpg", ".jpeg", ".png")
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(extensions):
                image_files.append(os.path.join(root, file))
    
    logger.info(f"{len(image_files)}件の画像が見つかりました")
    return image_files


def print_json_file(filepath):
    """JSONファイルの内容を表示"""
    if not os.path.exists(filepath):
        logger.warning(f"JSONファイルが存在しません: {filepath}")
        return
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"===== {filepath} の内容 =====")
        logger.info(f"エントリ数: {len(data)}")
        
        # 最初の3エントリーを表示
        count = 0
        for key, value in data.items():
            logger.info(f"キー: {key}")
            logger.info(f"値: {value}")
            count += 1
            if count >= 3:
                break
        
        logger.info("====================")
    
    except Exception as e:
        logger.error(f"JSONファイル読み込みエラー: {e}")


class TestOcrController:
    """OCRコントローラのテスト"""
    
    def __init__(self):
        self.settings = SettingsManager()
        self.models = ModelManager()
        self.ocr = OcrController(self.settings)
        
        # 結果を保存するフラグ
        self.processed_files = set()
        self.results = {}
        self.complete = False
        
        # シグナル接続
        self.ocr.text_extracted.connect(self.on_text_extracted)
        self.ocr.processing_progress.connect(self.on_progress)
        self.ocr.all_completed.connect(self.on_completed)
    
    def on_text_extracted(self, image_path, text):
        """テキスト抽出完了時のコールバック"""
        logger.info(f"OCR結果: {os.path.basename(image_path)} => {text[:30]}...")
        self.processed_files.add(image_path)
        self.results[image_path] = text
    
    def on_progress(self, file_path, current, total):
        """進捗通知時のコールバック"""
        logger.info(f"進捗: {current}/{total} - {os.path.basename(file_path)}")
    
    def on_completed(self):
        """すべての処理が完了したときのコールバック"""
        logger.info("OCR処理が完了しました")
        self.complete = True
    
    def run_test(self, image_dir):
        """テストを実行"""
        # 画像を列挙
        image_files = list_image_files(image_dir)
        if not image_files:
            logger.error("テスト対象の画像がありません")
            return False
        
        # 設定を表示
        config = load_config()
        logger.info(f"設定: {config}")
        
        # OCR処理を開始
        logger.info("OCR処理を開始します...")
        self.ocr.start_ocr(image_files, None)
        
        # 完了を待つ
        import time
        start_time = time.time()
        timeout = 60  # 最大待機時間（秒）
        
        while not self.complete and time.time() - start_time < timeout:
            # Qt のイベントループを手動で回す（ヘッドレスモードのため）
            from PyQt6.QtCore import QCoreApplication
            QCoreApplication.processEvents()
            time.sleep(0.1)
        
        # 結果を表示
        if self.complete:
            logger.info(f"処理完了: {len(self.processed_files)}/{len(image_files)} ファイル")
            
            # キャッシュファイルの内容を表示
            print_json_file(OCR_CACHE_FILE)
            print_json_file(DETECTION_RESULTS_FILE)
            
            # CSVファイルの内容を表示
            csv_path = config['output']['csv_path']
            if os.path.exists(csv_path):
                logger.info(f"CSVファイルが作成されました: {csv_path}")
                with open(csv_path, 'r', encoding='utf-8') as f:
                    logger.info(f"CSV内容: {f.read()[:500]}...")
            
            return True
        else:
            logger.error(f"タイムアウト: {len(self.processed_files)}/{len(image_files)} ファイルが処理されました")
            return False


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='OCR処理のヘッドレステスト')
    parser.add_argument('--dir', '-d', default=test_img_dir, help='テスト用画像ディレクトリ')
    args = parser.parse_args()
    
    logger.info("======== OCR処理ヘッドレステスト開始 ========")
    
    # Qtアプリケーション作成
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    
    # テスト実行
    test = TestOcrController()
    success = test.run_test(args.dir)
    
    # 結果表示
    logger.info("======== テスト結果 ========")
    if success:
        logger.info("テスト成功: OCR処理が正常に完了しました")
    else:
        logger.error("テスト失敗: OCR処理が正常に完了しませんでした")
    
    logger.info("======== OCR処理ヘッドレステスト終了 ========")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main()) 