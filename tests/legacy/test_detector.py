#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
検出モジュールのユニットテスト
"""

"""テスト対象: src\photocategorizer\models\detector.py (バックエンドモジュール)"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# 親ディレクトリをパスに追加
parent_dir = str(Path(__file__).parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from src.photocategorizer.models.detector import init_grounding_dino_sam, detect_objects_in_image


class TestDetector(unittest.TestCase):
    """検出モジュールのテスト"""
    
    def test_init_grounding_dino_sam_mock_environment(self):
        """モック環境でのモデル初期化テスト"""
        # モックモジュールを作成
        mock_gdino = MagicMock()
        mock_gdino._mock_name = "mock_groundingdino"
        mock_sam = MagicMock()
        mock_sam._mock_name = "mock_segmentanything"
        
        # sys.modulesにモックを追加
        with patch.dict(sys.modules, {
            'rf_groundingdino': mock_gdino,
            'rf_segment_anything': mock_sam
        }):
            detector = init_grounding_dino_sam(use_gpu=False)
            
            # MockDetectorクラスのインスタンスが返されるか確認
            self.assertIsNotNone(detector)
            self.assertTrue(hasattr(detector, 'predict'))
    
    @patch('src.photocategorizer.models.detector.init_grounding_dino_sam')
    def test_detect_objects_in_image(self, mock_init):
        """オブジェクト検出のテスト"""
        # モックモデルを作成
        mock_model = MagicMock()
        mock_model.predict.return_value = (
            ["test_label"],  # labels
            [[100, 100, 200, 200]],  # boxes
            [0.95]  # scores
        )
        mock_init.return_value = mock_model
        
        # テスト用の画像パスとプロンプト
        image_path = "test_image.jpg"
        prompt = "test_prompt"
        
        # 検出を実行
        with patch('cv2.imread') as mock_imread:
            # cv2.imreadのモック設定
            mock_img = MagicMock()
            mock_img.shape = (1000, 1000, 3)
            mock_imread.return_value = mock_img
            
            # 検出関数を呼び出し
            results = detect_objects_in_image(image_path, prompt)
            
            # 結果を検証
            self.assertIsNotNone(results)
            self.assertIsInstance(results, list)
            
            # 少なくとも1つの検出結果があるか
            if len(results) > 0:
                # 結果の形式を確認
                result = results[0]
                self.assertIn('bbox', result)
                self.assertIn('score', result)
                self.assertIn('label', result)
                self.assertIn('image_size', result)


if __name__ == "__main__":
    unittest.main() 