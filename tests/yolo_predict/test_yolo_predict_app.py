#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOLO予測アプリケーションのテスト
"""

"""テスト対象: src/yolo_predict_app.py (エントリーポイント), src/backup/yolo_predict_app.py (エントリーポイント)"""
import sys
import os
import unittest
from pathlib import Path
import shutil

# プロジェクトルートをPython pathに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt, QSettings

from src.yolo_predict_app import YoloPredictApp


class TestYoloPredictApp(unittest.TestCase):
    """YoloPredictAppのテストクラス"""

    @classmethod
    def setUpClass(cls):
        """テスト全体の前処理"""
        cls.app = QApplication(sys.argv)
        
        # 既存の設定をバックアップ
        cls.settings = QSettings("YoloPredictApp", "settings")
        cls.original_settings = {}
        for key in cls.settings.allKeys():
            cls.original_settings[key] = cls.settings.value(key)
        cls.settings.clear()

    @classmethod
    def tearDownClass(cls):
        """テスト全体の後処理"""
        # 設定を元に戻す
        cls.settings.clear()
        for key, value in cls.original_settings.items():
            cls.settings.setValue(key, value)

    def setUp(self):
        """各テスト前の処理"""
        self.window = YoloPredictApp()

    def tearDown(self):
        """各テスト後の処理"""
        self.window.close()

    def test_app_initialization(self):
        """アプリが正常に初期化されるかテスト"""
        self.assertIsNotNone(self.window)
        self.assertEqual(self.window.windowTitle(), "YOLO 画像予測アプリ")

    def test_ui_components(self):
        """UIコンポーネントが存在するかテスト"""
        # 主要なUIコンポーネントが存在するか確認
        self.assertIsNotNone(self.window.ui.model_combo)
        self.assertIsNotNone(self.window.ui.img_dir_edit)
        self.assertIsNotNone(self.window.ui.subfolder_check)
        self.assertIsNotNone(self.window.ui.conf_spin)
        self.assertIsNotNone(self.window.ui.predict_btn)
        self.assertIsNotNone(self.window.ui.results_table)

    def test_model_selection(self):
        """モデル選択機能のテスト"""
        # コンボボックスにアイテムがあるか確認
        self.assertGreater(self.window.ui.model_combo.count(), 0)
        
        # モデル選択の変更テスト（カテゴリヘッダーは飛ばす）
        for i in range(self.window.ui.model_combo.count()):
            if self.window.ui.model_combo.itemData(i) is not None:
                self.window.ui.model_combo.setCurrentIndex(i)
                self.assertEqual(self.window.ui.model_combo.currentIndex(), i)
                # 少なくとも1つのモデルをテストすれば十分
                break
                
    def test_ui_operations(self):
        """UIの基本操作が機能するかテスト"""
        # 信頼度閾値の変更
        new_conf = 0.45
        self.window.ui.conf_spin.setValue(new_conf)
        self.assertEqual(self.window.ui.conf_spin.value(), new_conf)
        
        # サブフォルダチェックボックスの変更
        current_state = self.window.ui.subfolder_check.isChecked()
        self.window.ui.subfolder_check.setChecked(not current_state)
        self.assertEqual(self.window.ui.subfolder_check.isChecked(), not current_state)


if __name__ == "__main__":
    unittest.main() 