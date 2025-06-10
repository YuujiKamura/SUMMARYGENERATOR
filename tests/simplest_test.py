#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import os
import sys
import logging

# ロギング設定
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("simplest_test")

class SimplestTest(unittest.TestCase):
    """最もシンプルなテストケース"""
    
    def test_simple_assert(self):
        """最もシンプルなアサーション"""
        logger.info("シンプルなテストを実行中...")
        self.assertEqual(1, 1)
        logger.info("シンプルなテスト完了")
    
    def test_environment(self):
        """環境情報の出力"""
        logger.info(f"Python: {sys.version}")
        logger.info(f"実行ディレクトリ: {os.getcwd()}")
        logger.info(f"Pythonパス: {sys.path}")
        
        # インストール済みモジュールのリスト
        import pkg_resources
        installed_packages = pkg_resources.working_set
        installed_packages_list = sorted([f"{i.key} {i.version}" for i in installed_packages])
        logger.info(f"インストール済みパッケージ数: {len(installed_packages_list)}")
        logger.info("インストール済み主要パッケージ:")
        qt_packages = [pkg for pkg in installed_packages_list if "qt" in pkg.lower()]
        for pkg in qt_packages:
            logger.info(f"  - {pkg}")
        
        self.assertTrue(True)
        logger.info("環境情報テスト完了")

if __name__ == "__main__":
    logger.info("最もシンプルなテストを開始します")
    unittest.main(verbosity=2)
    logger.info("テスト完了") 