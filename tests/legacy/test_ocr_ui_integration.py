#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OCR結果をウィンドウに表示するための結合テスト
"""

import os
import sys
import time
import logging
from pathlib import Path

# プロジェクトルートをパスに追加
current_dir = Path(__file__).parent.absolute()
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

# PyQt6関連
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt, QTimer, QModelIndex

# アプリケーションのインポート
from app.controllers.settings_manager import SettingsManager
from app.controllers.model_manager import ModelManager
from app.controllers.ocr_controller import OcrController
from app.controllers.prediction_controller import PredictionController
from app.ui.photo_categorizer_window import PhotoCategorizerWindow

# テスト用ユーティリティ
from tests.utils import wait_for_processing

# ロギング設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # コンソールに出力
        logging.FileHandler('ocr_ui_test.log', encoding='utf-8')  # ファイルにも出力
    ]
)

logger = logging.getLogger('ocr_ui_test')

# テスト用の画像ディレクトリ
TEST_IMG_DIR = os.path.join(project_root, "test_images")


class OcrUiIntegrationTest:
    """OCR結果をUIに表示するテスト"""
    
    def __init__(self):
        """初期化"""
        self.app = QApplication(sys.argv)
        
        # コントローラー初期化
        self.settings = SettingsManager()
        self.models = ModelManager()
        self.predictor = PredictionController(self.settings, self.models)
        self.ocr = OcrController(self.settings)
        
        # メインウィンドウ初期化
        self.window = PhotoCategorizerWindow(
            self.settings, self.models, self.predictor, self.ocr
        )
        
        # テスト用のハンドラー追加
        self.window.ocr_requested.connect(self.on_ocr_requested)
        
        # テスト状態
        self.test_completed = False
        self.success = False
        self.test_steps = []
        self.step_index = 0
    
    def on_ocr_requested(self):
        """OCRリクエスト時のハンドラー"""
        logger.info("OCRが要求されました")
        
        # 画像パスのリストを取得
        image_paths = []
        for row in range(self.window.photo_model.rowCount()):
            index = self.window.photo_model.index(row, 0)
            path = index.data(Qt.ItemDataRole.UserRole)
            if path:
                image_paths.append(path)
        
        # OCR処理を開始
        if image_paths:
            logger.info(f"OCR処理開始: {len(image_paths)}件の画像")
            self.ocr.start_ocr(image_paths, None)
    
    def setup_test_steps(self):
        """テストのステップを設定"""
        self.test_steps = [
            {
                'action': lambda: self.window.show(),
                'description': "ウィンドウを表示",
                'delay': 500
            },
            {
                'action': lambda: self.window.scan_folder(TEST_IMG_DIR),
                'description': "テスト画像フォルダを読み込み",
                'delay': 1000
            },
            {
                'action': lambda: self.verify_images_loaded(),
                'description': "画像が読み込まれたことを確認",
                'delay': 500
            },
            {
                'action': lambda: self.window._on_ocr_button_clicked(),
                'description': "OCRボタンをクリック",
                'delay': 5000  # OCR処理完了待ち
            },
            {
                'action': lambda: self.check_caption_results(),
                'description': "キャプション結果を確認",
                'delay': 500
            },
            {
                'action': lambda: self.select_first_image(),
                'description': "最初の画像を選択",
                'delay': 500
            },
            {
                'action': lambda: self.verify_caption_display(),
                'description': "キャプション表示を確認",
                'delay': 500
            },
            {
                'action': lambda: self.test_orientation_change(),
                'description': "縦書き・横書き切替テスト",
                'delay': 1000
            },
            {
                'action': lambda: self.complete_test(True),
                'description': "テスト完了",
                'delay': 0
            }
        ]
    
    def verify_images_loaded(self):
        """画像が読み込まれたことを確認"""
        count = self.window.photo_model.rowCount()
        logger.info(f"読み込まれた画像数: {count}")
        return count > 0
    
    def check_caption_results(self):
        """キャプション結果を確認"""
        caption_count = len(self.window.image_captions)
        logger.info(f"処理されたキャプション数: {caption_count}")
        return caption_count > 0
    
    def select_first_image(self):
        """最初の画像を選択"""
        if self.window.photo_model.rowCount() > 0:
            index = self.window.photo_model.index(0, 0)
            self.window._on_photo_clicked(index)
            return True
        return False
    
    def verify_caption_display(self):
        """キャプション表示を確認"""
        # 現在の画像とそのキャプション
        if not self.window.current_image_path:
            logger.error("選択された画像がありません")
            return False
        
        caption = self.window.caption_label.text()
        logger.info(f"表示されているキャプション: {caption}")
        
        # キャプションがあるかどうかをチェック
        if "検出されていません" in caption and self.window.current_image_path in self.window.image_captions:
            logger.error("キャプションがUIに反映されていません")
            return False
        
        return True
    
    def test_orientation_change(self):
        """縦書き・横書き切替テスト"""
        # 現在の方向を保存
        original_orientation = self.window.caption_orientation
        
        # 縦書きに変更
        self.window.vertical_radio.setChecked(True)
        if self.window.caption_orientation != "vertical":
            logger.error("縦書きモードに切り替わりませんでした")
            return False
        
        # 横書きに戻す
        self.window.horizontal_radio.setChecked(True)
        if self.window.caption_orientation != "horizontal":
            logger.error("横書きモードに切り替わりませんでした")
            return False
        
        return True
    
    def complete_test(self, result):
        """テストを完了"""
        self.success = result
        self.test_completed = True
        self.window.close()
    
    def run_next_step(self):
        """次のテストステップを実行"""
        if self.step_index >= len(self.test_steps):
            # すべてのステップが完了
            self.complete_test(True)
            return
        
        step = self.test_steps[self.step_index]
        logger.info(f"ステップ {self.step_index + 1}/{len(self.test_steps)}: {step['description']}")
        
        # ステップのアクションを実行
        result = step['action']()
        
        # 検証ステップの場合は結果をチェック
        if result is not None and result is False:
            logger.error(f"ステップ {self.step_index + 1} が失敗しました: {step['description']}")
            self.complete_test(False)
            return
        
        # 次のステップのタイマーをセット
        self.step_index += 1
        
        if self.step_index < len(self.test_steps):
            QTimer.singleShot(step['delay'], self.run_next_step)
    
    def run_test(self):
        """テストを実行"""
        logger.info("======== OCR UI統合テスト開始 ========")
        
        # テストステップを設定
        self.setup_test_steps()
        
        # 最初のステップを開始
        QTimer.singleShot(0, self.run_next_step)
        
        # アプリケーションのイベントループを開始
        self.app.exec()
        
        # テスト結果を報告
        logger.info("======== テスト結果 ========")
        if self.success:
            logger.info("テスト成功: OCR結果をUIに表示できました")
        else:
            logger.error("テスト失敗: OCR結果をUIに表示できませんでした")
        
        logger.info("======== OCR UI統合テスト終了 ========")
        
        return self.success


def main():
    """メイン関数"""
    test = OcrUiIntegrationTest()
    success = test.run_test()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main()) 