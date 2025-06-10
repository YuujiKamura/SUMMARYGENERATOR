#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import unittest
import logging

# ロギング設定
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mini_test")

try:
    from PyQt6.QtWidgets import QApplication, QLabel
    from PyQt6.QtCore import Qt
    qt_available = True
except ImportError:
    logger.error("PyQt6をインポートできません")
    qt_available = False


@unittest.skipIf(not qt_available, "PyQt6が利用できないためスキップします")
class TestMinimalQt(unittest.TestCase):
    """最小限のQtテスト"""
    
    @classmethod
    def setUpClass(cls):
        """テスト開始前の準備"""
        logger.info("最小限のQtテストを開始します")
        cls.app = QApplication.instance() or QApplication(sys.argv)
    
    @classmethod
    def tearDownClass(cls):
        """テスト終了時のクリーンアップ"""
        logger.info("最小限のQtテストを終了します")
        if QApplication.instance():
            QApplication.instance().quit()
    
    def test_create_label(self):
        """QWidgetが作成できるかテスト"""
        logger.info("QLabel作成テスト")
        label = QLabel("テストラベル")
        self.assertEqual(label.text(), "テストラベル")
        logger.info("QLabel作成テスト完了")


if __name__ == "__main__":
    unittest.main(verbosity=2) 