#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
実際のGoogle Cloud Vision APIを使用したOCRテスト
"""

import os
import sys
import json
import logging
import tempfile
from pathlib import Path
from typing import List

# プロジェクトルートをパスに追加
current_dir = Path(__file__).parent.absolute()
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

# PyQt6関連
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QCoreApplication

# アプリケーションのインポート
from app.controllers.ocr_controller import OcrController
from app.controllers.settings_manager import SettingsManager
from app.utils.config_loader import load_config
from app.utils.paths import OCR_CACHE_FILE, DETECTION_RESULTS_FILE, DATA_DIR

# ロギング設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # コンソールに出力
        logging.FileHandler('ocr_real_test.log', encoding='utf-8')  # ファイルにも出力
    ]
)

logger = logging.getLogger('ocr_real_test')

# テスト用の画像ディレクトリ
TEST_IMG_DIR = os.path.join(project_root, "test_images")


def list_test_images() -> List[str]:
    """テスト用の画像ファイルをリストアップ"""
    if not os.path.exists(TEST_IMG_DIR):
        logger.error(f"テスト画像ディレクトリが存在しません: {TEST_IMG_DIR}")
        return []
    
    logger.info(f"テスト画像ディレクトリをスキャン中: {TEST_IMG_DIR}")
    image_files = []
    extensions = (".jpg", ".jpeg", ".png")
    
    for file in os.listdir(TEST_IMG_DIR):
        if file.lower().endswith(extensions):
            image_files.append(os.path.join(TEST_IMG_DIR, file))
    
    logger.info(f"{len(image_files)}件のテスト画像が見つかりました")
    return image_files


def print_ocr_result(result_file):
    """OCR結果を表示"""
    if not os.path.exists(result_file):
        logger.warning(f"結果ファイルが存在しません: {result_file}")
        return
    
    try:
        with open(result_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"===== {result_file} の内容 =====")
        logger.info(f"エントリ数: {len(data)}")
        
        # 結果を表示
        for path, text in data.items():
            filename = os.path.basename(path)
            logger.info(f"ファイル: {filename}")
            logger.info(f"抽出テキスト: {text}")
        
        logger.info("====================")
    
    except Exception as e:
        logger.error(f"結果ファイル読み込みエラー: {e}")


class RealOcrTest:
    """実際のVision APIを使用したOCRテスト"""
    
    def __init__(self):
        """初期化"""
        self.settings = SettingsManager()
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
        logger.info(f"OCR結果: {os.path.basename(image_path)} => {text}")
        self.processed_files.add(image_path)
        self.results[image_path] = text
    
    def on_progress(self, file_path, current, total):
        """進捗通知時のコールバック"""
        logger.info(f"進捗: {current}/{total} - {os.path.basename(file_path)}")
    
    def on_completed(self):
        """すべての処理が完了したときのコールバック"""
        logger.info("OCR処理が完了しました")
        self.complete = True
    
    def run_test(self, image_files):
        """テストを実行"""
        if not image_files:
            logger.error("テスト対象の画像がありません")
            return False
        
        # 設定を表示
        config = load_config()
        logger.info(f"使用設定: {config}")
        
        # 認証情報ファイルの存在確認
        credentials_file = config['vision_api']['credentials_file']
        if not os.path.exists(credentials_file):
            logger.error(f"認証情報ファイルが見つかりません: {credentials_file}")
            logger.error("認証情報ファイルが必要です。config.jsonを確認してください。")
            return False
        
        # OCR処理を開始
        logger.info(f"OCR処理を開始します... (対象: {len(image_files)}ファイル)")
        self.ocr.start_ocr(image_files, None)
        
        # 完了を待つ
        import time
        start_time = time.time()
        timeout = 120  # 最大待機時間（秒）
        
        while not self.complete and time.time() - start_time < timeout:
            # Qt のイベントループを手動で回す
            QCoreApplication.processEvents()
            time.sleep(0.1)
        
        # 結果を表示
        if self.complete:
            logger.info(f"処理完了: {len(self.processed_files)}/{len(image_files)} ファイル")
            
            # キャッシュファイルの内容を表示
            print_ocr_result(OCR_CACHE_FILE)
            print_ocr_result(DETECTION_RESULTS_FILE)
            
            # CSVファイルの内容を表示
            csv_path = config['output']['csv_path']
            if os.path.exists(csv_path):
                logger.info(f"CSVファイルが作成されました: {csv_path}")
                with open(csv_path, 'r', encoding='utf-8') as f:
                    logger.info(f"CSV内容: {f.read()}")
            
            return True
        else:
            logger.error(f"タイムアウト: {len(self.processed_files)}/{len(image_files)} ファイルが処理されました")
            return False


def main():
    """メイン関数"""
    logger.info("======== 実際のOCRテスト開始 ========")
    
    # Qtアプリケーション作成
    app = QApplication(sys.argv)
    
    # テスト画像をリストアップ
    image_files = list_test_images()
    
    # テスト実行
    test = RealOcrTest()
    success = test.run_test(image_files)
    
    # 結果表示
    logger.info("======== テスト結果 ========")
    if success:
        logger.info("テスト成功: OCR処理が正常に完了しました")
    else:
        logger.error("テスト失敗: OCR処理が正常に完了しませんでした")
    
    logger.info("======== 実際のOCRテスト終了 ========")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main()) 