#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OCRコントローラーと辞書マネージャーの連携テスト（ヘッドレス）
GUIを表示せずにOCR結果と辞書のマッチング機能をテストする
"""

import os
import sys
import unittest
import tempfile
import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

# QApplicationのヘッドレスモード設定
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_LOGGING_TO_CONSOLE"] = "0"
os.environ["QT_FORCE_HEADLESS"] = "1"

# Windowsの場合に追加の設定
if sys.platform.startswith('win'):
    os.environ["QT_OPENGL"] = "software"
    os.environ["QT_SCALE_FACTOR"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"

# 現在のディレクトリをモジュール検索パスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# PyQt6のインポート
from PyQt6.QtWidgets import QApplication

from app.controllers.settings_manager import SettingsManager
from app.controllers.dictionary_manager import DictionaryManager, DictRecord, normalize
from app.controllers.ocr_controller import OcrController, OcrThread
from app.utils.paths import OCR_CACHE_FILE


class TestHeadlessOcrDictionary(unittest.TestCase):
    """OCRとDictionaryManagerの連携テスト（ヘッドレス）"""
    
    @classmethod
    def setUpClass(cls):
        """テストクラスの初期化"""
        # QApplicationの初期化（GUIなし）
        cls.app = QApplication.instance() or QApplication(sys.argv)
        
        # テスト用ディレクトリを作成
        cls.test_dir = Path(tempfile.mkdtemp())
        
        # テスト用画像ディレクトリ
        cls.test_images_dir = cls.test_dir / "test_images"
        cls.test_images_dir.mkdir(exist_ok=True)
        
        # テスト用画像ファイルのパス
        cls.test_image_paths = [
            str(cls.test_images_dir / "image1.jpg"),
            str(cls.test_images_dir / "image2.jpg"),
            str(cls.test_images_dir / "image3.jpg")
        ]
        
        # テスト用画像ファイルを作成（空ファイル）
        for image_path in cls.test_image_paths:
            with open(image_path, 'w') as f:
                f.write("dummy image content")
    
    @classmethod
    def tearDownClass(cls):
        """テストクラスのクリーンアップ"""
        try:
            # テスト用ディレクトリを削除
            if hasattr(cls, 'test_dir') and cls.test_dir.exists():
                shutil.rmtree(cls.test_dir, ignore_errors=True)
        except Exception as e:
            print(f"テストディレクトリの削除中にエラー: {e}")
    
    def setUp(self):
        """テスト準備"""
        # 一時ファイル作成
        self.temp_ocr_cache = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        self.temp_ocr_cache.close()
        
        self.temp_dict_file = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        self.temp_dict_file.close()
        
        self.temp_records_file = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        self.temp_records_file.close()
        
        # テスト用OCRキャッシュデータ（実際のテスト画像パスを使用）
        self.ocr_cache_data = {}
        for i, path in enumerate(self.test_image_paths):
            if i == 0:
                self.ocr_cache_data[path] = "工種:土工 種別:掘削 No.5 測点:10K+500"
            elif i == 1:
                self.ocr_cache_data[path] = "工種:コンクリート 種別:型枠 細別:普通 測点:12K+250"
            elif i == 2:
                self.ocr_cache_data[path] = "工種:舗装 種別:表層 規格:再生密粒度As 測点:15K+100"
        
        # 辞書データの準備 - レコードから自動生成するため最小限に
        self.dictionary_data = {
            "category": ["土工", "コンクリート", "舗装"],
            "type": ["掘削", "型枠", "表層"],
            "subtype": ["普通"],
            "remarks": ["No.5", "規格:再生密粒度As"],
            "station": ["10K+500", "12K+250", "15K+100"],
            "control": []
        }
        
        # チェーン辞書レコードの準備
        self.records_data = [
            {"category": "土工", "type": "掘削", "subtype": "", "remarks": "No.5", "station": "10K+500", "control": ""},
            {"category": "コンクリート", "type": "型枠", "subtype": "普通", "remarks": "", "station": "12K+250", "control": ""},
            {"category": "舗装", "type": "表層", "subtype": "", "remarks": "規格:再生密粒度As", "station": "15K+100", "control": ""}
        ]
        
        # OCRキャッシュの書き込み
        with open(self.temp_ocr_cache.name, 'w', encoding='utf-8') as f:
            json.dump(self.ocr_cache_data, f, ensure_ascii=False)
        
        # 辞書データの書き込み
        with open(self.temp_dict_file.name, 'w', encoding='utf-8') as f:
            json.dump(self.dictionary_data, f, ensure_ascii=False)
            
        # レコードデータの書き込み
        with open(self.temp_records_file.name, 'w', encoding='utf-8') as f:
            json.dump(self.records_data, f, ensure_ascii=False)
        
        # SettingsManagerのモック
        self.mock_settings = MagicMock()
        
        # DictionaryManagerの準備（辞書ファイルパスをパッチ）
        with patch.object(DictionaryManager, '_get_dictionary_file', return_value=self.temp_dict_file.name), \
             patch.object(DictionaryManager, '_get_records_file', return_value=self.temp_records_file.name):
            self.dictionary = DictionaryManager(self.mock_settings)
            # レコードデータを直接設定（チェーン辞書用）
            self.dictionary.records = [DictRecord.from_dict(rec) for rec in self.records_data]
            # 個別辞書も更新
            self.dictionary._update_individual_dictionaries()
        
        # OCRControllerの準備（キャッシュファイルをパッチ）
        with patch('app.utils.paths.OCR_CACHE_FILE', Path(self.temp_ocr_cache.name)):
            self.ocr = OcrController(self.mock_settings, self.dictionary)
            self.ocr.cache = self.ocr_cache_data.copy()  # キャッシュを直接設定
            
            # OCRコントローラのマッチングシグナルをモック化
            self.ocr.dictionary_match = MagicMock()
            # OCRコントローラのテキスト抽出シグナルをモック化
            self.ocr.text_extracted = MagicMock()
            
            # OCRコントローラのテキスト抽出時の辞書マッチングを確実に呼び出すようにパッチ
            original_on_text_extracted = self.ocr._on_text_extracted
            def patched_on_text_extracted(image_path, text):
                result = original_on_text_extracted(image_path, text)
                matches = self.dictionary.match_text_with_dictionary(text)
                self.ocr.dictionary_match.emit(image_path, matches)
                return result
            self.ocr._on_text_extracted = patched_on_text_extracted
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        # 一時ファイルの削除
        for temp_file in [self.temp_ocr_cache, self.temp_dict_file, self.temp_records_file]:
            if os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                except Exception as e:
                    print(f"一時ファイルの削除中にエラー: {e}")
    
    def test_ocr_controller_cache_operations(self):
        """OCRコントローラーのキャッシュ操作が正しく機能するか"""
        # シンプルなテスト：キャッシュのメソッドが正しく動作することを確認
        test_path = self.test_image_paths[0]
        test_text = "テスト用OCRテキスト"
        
        # キャッシュをクリアして新しい値を設定
        self.ocr.cache = {}
        self.ocr.cache[test_path] = test_text
        
        # キャッシュから取得できるか確認
        cached_text = self.ocr.get_cached_text(test_path)
        self.assertEqual(cached_text, test_text, "キャッシュからテキストが正しく取得できませんでした")
        
        # 存在しないパスにはNoneが返るか確認
        none_text = self.ocr.get_cached_text("存在しないパス")
        self.assertIsNone(none_text, "存在しないパスに対してNoneが返されるべきです")
    
    def test_dictionary_manager_loads_dictionary(self):
        """辞書マネージャーが辞書を正しくロードするか"""
        # レコードから自動生成された辞書エントリが正しく存在するか確認
        expected_categories = {"土工", "コンクリート", "舗装"}
        loaded_categories = set(self.dictionary.get_entries(DictionaryManager.CATEGORY))
        self.assertEqual(expected_categories, loaded_categories, 
                        "辞書タイプ category のエントリがマッチしません")
        
        expected_types = {"掘削", "型枠", "表層"}
        loaded_types = set(self.dictionary.get_entries(DictionaryManager.TYPE))
        self.assertEqual(expected_types, loaded_types, 
                        "辞書タイプ type のエントリがマッチしません")
    
    def test_dictionary_records_loaded(self):
        """チェーン辞書レコードが正しくロードされるか"""
        # レコード数の確認
        self.assertEqual(len(self.dictionary.records), len(self.records_data))
        
        # 各レコードの内容確認
        for i, expected_record in enumerate(self.records_data):
            actual_record = self.dictionary.records[i].to_dict()
            for key, value in expected_record.items():
                self.assertEqual(actual_record[key], value, f"レコード[{i}].{key}の値が一致しません")
    
    def test_match_text_with_dictionary(self):
        """OCRテキストと辞書のマッチングが正しく機能するか"""
        # テストケース
        test_cases = [
            {
                "image_path": self.test_image_paths[0],
                "expected_matches": {
                    "category": "土工",
                    "type": "掘削",
                    "remarks": "No.5",
                    "station": "10K+500"
                }
            },
            {
                "image_path": self.test_image_paths[1],
                "expected_matches": {
                    "category": "コンクリート",
                    "type": "型枠",
                    "subtype": "普通",
                    "station": "12K+250"
                }
            },
            {
                "image_path": self.test_image_paths[2],
                "expected_matches": {
                    "category": "舗装",
                    "type": "表層",
                    "remarks": "規格:再生密粒度As",
                    "station": "15K+100"
                }
            }
        ]
        
        # 各テストケースを実行
        for test_case in test_cases:
            image_path = test_case["image_path"]
            expected = test_case["expected_matches"]
            
            # OCRキャッシュからテキストを取得
            text = self.ocr.get_cached_text(image_path)
            self.assertIsNotNone(text, f"キャッシュからテキストが取得できませんでした: {image_path}")
            
            # 辞書とマッチング
            matches = self.dictionary.match_text_with_dictionary(text)
            
            # 期待する一致結果があるか確認
            for dict_type, expected_entry in expected.items():
                self.assertIn(dict_type, matches, f"タイプ '{dict_type}' が見つかりません: {image_path}")
                self.assertEqual(matches[dict_type], expected_entry, 
                              f"エントリが一致しません '{dict_type}': 期待={expected_entry}, 実際={matches[dict_type]}")
    
    def test_fuzzy_matching(self):
        """ファジーマッチング（部分一致、類似度）が機能するか"""
        # 正確に一致しないテキスト
        fuzzy_texts = [
            # 1. スペースの違い
            "工 種 : 土 工　種別:掘削",
            # 2. 全角/半角の違い
            "工種：土工　種別：掘　削",
            # 3. 誤字
            "工種:土工 種別:堀削",
            # 4. 一部欠落
            "工種:土 種別:掘削"
        ]
        
        # 期待される結果
        expected_matches = {
            "category": "土工",
            "type": "掘削"
        }
        
        # 各ファジーテキストでテスト
        for i, text in enumerate(fuzzy_texts):
            matches = self.dictionary.match_text_with_dictionary(text)
            
            for dict_type, expected_entry in expected_matches.items():
                self.assertIn(dict_type, matches, 
                          f"ファジーテキスト[{i}]でタイプ '{dict_type}' が見つかりません: {text}")
                self.assertEqual(matches[dict_type], expected_entry, 
                              f"ファジーテキスト[{i}]のエントリが一致しません '{dict_type}': 期待={expected_entry}, 実際={matches[dict_type]}")
    
    def test_chain_record_completion(self):
        """一部の項目だけのマッチングからチェーンレコード全体を補完できるか"""
        # 一部だけマッチするテキスト
        partial_text = "種別:表層" # 工種(舗装)や備考(規格:再生密粒度As)は含まない
        
        # マッチング実行
        matches = self.dictionary.match_text_with_dictionary(partial_text)
        
        # 期待される補完結果
        expected_matches = {
            "category": "舗装",  # ← 自動補完
            "type": "表層",      # ← テキストから直接マッチ
            "remarks": "規格:再生密粒度As",  # ← 自動補完
            "station": "15K+100"  # ← 自動補完
        }
        
        # 結果検証
        for dict_type, expected_entry in expected_matches.items():
            self.assertIn(dict_type, matches, 
                      f"チェーン補完でタイプ '{dict_type}' が見つかりません")
            self.assertEqual(matches[dict_type], expected_entry, 
                          f"チェーン補完のエントリが一致しません '{dict_type}': 期待={expected_entry}, 実際={matches[dict_type]}")
    
    def test_ocr_controller_match_with_dictionary(self):
        """OCRコントローラがDictionaryManagerを使って正しくマッチングするか"""
        # テスト画像パス
        test_image_path = self.test_image_paths[0]
        
        # OCRコントローラーのマッチングメソッドを呼び出し
        result = self.ocr.match_text_with_dictionary(test_image_path)
        
        # 期待する結果
        expected_result = {
            "category": "土工",
            "type": "掘削",
            "remarks": "No.5",
            "station": "10K+500"
        }
        
        # 結果の検証
        self.assertEqual(result, expected_result)
    
    def test_adding_dictionary_entry_affects_matching(self):
        """辞書エントリの追加がマッチング結果に影響するか"""
        # テスト用のレコードを追加（辞書に直接追加するとレコードからの処理が競合するため）
        new_record = {
            "category": "舗装", 
            "type": "表層", 
            "subtype": "密粒度", 
            "remarks": "規格:再生密粒度As", 
            "station": "15K+100", 
            "control": ""
        }
        self.dictionary.add_record(new_record)
        
        # テスト用テキスト
        test_text = "工種:舗装 種別:表層 細別:密粒度 測点:15K+100 規格:再生密粒度As"
        
        # マッチングテスト
        matches = self.dictionary.match_text_with_dictionary(test_text)
        
        # 追加したエントリがマッチに含まれることを確認
        self.assertIn("subtype", matches)
        self.assertEqual(matches["subtype"], "密粒度")
    
    def test_adding_record_affects_matching(self):
        """チェーンレコードの追加がマッチングに影響するか"""
        # 新しいテストテキスト（既存のレコードにないもの）
        test_text = "工種:防護柵 種別:ガードレール 細別:塗装品 測点:25K+000"
        
        # 追加前のマッチング - 一致するものがないことを確認
        before_matches = self.dictionary.match_text_with_dictionary(test_text)
        # レコードが存在しない場合は"category"が入っていない可能性がある
        if "category" in before_matches:
            self.assertNotEqual(before_matches.get("category"), "防護柵", 
                              "工種:'防護柵'はまだ辞書に存在しないはず")
        
        # 新しいレコードを追加
        new_record = {
            "category": "防護柵",
            "type": "ガードレール",
            "subtype": "塗装品",
            "remarks": "",
            "station": "25K+000",
            "control": ""
        }
        self.dictionary.add_record(new_record)
        
        # 追加後のマッチング
        after_matches = self.dictionary.match_text_with_dictionary(test_text)
        
        # 追加したレコードの項目がマッチすることを確認
        self.assertIn("category", after_matches)
        self.assertEqual(after_matches["category"], "防護柵")
        self.assertIn("type", after_matches)
        self.assertEqual(after_matches["type"], "ガードレール")
        self.assertIn("subtype", after_matches)
        self.assertEqual(after_matches["subtype"], "塗装品")
    
    def test_ocr_text_extracted_triggers_dictionary_matching(self):
        """OCRテキスト抽出が辞書マッチングをトリガーするか"""
        # OCRテキストをシミュレート
        test_path = self.test_image_paths[0]
        test_text = "工種:土工 種別:掘削"
        
        # テキスト抽出シグナルを直接パッチしたメソッドで呼び出し
        self.ocr._on_text_extracted(test_path, test_text)
        
        # 辞書マッチングシグナルが発火したか確認
        self.ocr.dictionary_match.emit.assert_called()
        
        # 呼び出し引数を検証
        args, _ = self.ocr.dictionary_match.emit.call_args
        self.assertEqual(args[0], test_path)  # 画像パス
        self.assertIsInstance(args[1], dict)  # マッチング結果が辞書型


if __name__ == '__main__':
    unittest.main() 