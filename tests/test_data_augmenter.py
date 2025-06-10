#!/usr/bin/env python3
"""
データ拡張機能のユニットテスト
"""

"""テスト対象: src/utils/data_augmenter.py (バックエンドモジュール)"""
import sys
import os
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np
import pytest

# テスト対象のモジュールのパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent))

# テスト対象のモジュールをインポート
try:
    from src.utils.data_augmenter import augment_dataset, DataAugmentThread
except ImportError:
    from utils.data_augmenter import augment_dataset, DataAugmentThread

@pytest.mark.unit
@pytest.mark.data_augmentation
class TestDataAugmenter(unittest.TestCase):
    """データ拡張機能のユニットテスト"""
    
    @pytest.mark.unit
    @pytest.mark.data_augmentation
    def setUp(self):
        """各テストケースのセットアップ"""
        # テスト用一時ディレクトリを作成
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        # テスト用の画像とラベルディレクトリ
        self.img_dir = self.temp_path / "images"
        self.label_dir = self.temp_path / "labels"
        self.dst_dir = self.temp_path / "augmented"
        
        # テスト用ディレクトリ作成
        self.img_dir.mkdir(parents=True)
        self.label_dir.mkdir(parents=True)
        
        # テスト用ダミーファイル作成
        # テスト用ダミー画像（中身は重要ではない、存在するだけで良い）
        self.dummy_img = self.img_dir / "test.jpg"
        with open(self.dummy_img, "wb") as f:
            f.write(b"dummy image data")
        
        # テスト用ダミーラベル（YOLOフォーマット）
        self.dummy_label = self.label_dir / "test.txt"
        with open(self.dummy_label, "w") as f:
            f.write("0 0.5 0.5 0.2 0.2\n")  # クラス0、中央x,y、幅、高さ
    
    @pytest.mark.unit
    @pytest.mark.data_augmentation
    def tearDown(self):
        """各テストケースの後処理"""
        self.temp_dir.cleanup()
    
    @pytest.mark.unit
    @pytest.mark.data_augmentation
    @patch('cv2.imread')
    @patch('cv2.imwrite')
    @patch('PIL.Image.open')
    @patch('PIL.Image.Image.save')
    def test_augment_dataset_function(self, mock_save, mock_open, mock_imwrite, mock_imread):
        """augment_dataset関数のテスト"""
        # PILとOpenCVのモック
        mock_img = MagicMock()
        mock_open.return_value = mock_img
        mock_img.size = (640, 480)
        
        # OpenCVのモック
        mock_imread.return_value = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_imwrite.return_value = True
        
        # augment_dataset関数を呼び出す
        result = augment_dataset(
            src_img_dir=str(self.img_dir),
            src_label_dir=str(self.label_dir),
            dst_dir=str(self.dst_dir),
            n_augment=3
        )
        
        # 結果が正しいか確認
        self.assertEqual(result["original_images"], 1)  # ダミー画像1枚
        self.assertEqual(result["augmented_images"], 3)  # 3倍に拡張
        self.assertEqual(result["total_images"], 4)  # 合計4枚
        
        # dataset.yamlが作成されたか確認
        yaml_path = self.dst_dir / "dataset.yaml"
        self.assertTrue(yaml_path.exists())
        
        # 画像の保存が呼ばれたか確認
        self.assertEqual(mock_imwrite.call_count, 3)  # 3枚の拡張画像
    
    @pytest.mark.unit
    @pytest.mark.data_augmentation
    def test_data_augment_thread(self):
        """DataAugmentThreadのテスト"""
        # シグナル受信のためのモック
        output_received = MagicMock()
        process_finished = MagicMock()
        
        # モック関数を使用してaugment_datasetをパッチ
        with patch('src.utils.data_augmenter.augment_dataset', return_value={
            "original_images": 10,
            "augmented_images": 30,
            "total_images": 40,
            "yaml_file": "test/dataset.yaml"
        }) as mock_augment:
            
            # スレッドを作成
            thread = DataAugmentThread(
                src_img_dir=str(self.img_dir),
                src_label_dir=str(self.label_dir),
                dst_dir=str(self.dst_dir),
                n_augment=3
            )
            
            # シグナルを接続
            thread.output_received.connect(output_received)
            thread.process_finished.connect(process_finished)
            
            # スレッドを実行
            thread.run()
            
            # augment_datasetが正しいパラメータで呼ばれたか確認
            mock_augment.assert_called_once_with(
                src_img_dir=str(self.img_dir),
                src_label_dir=str(self.label_dir),
                dst_dir=str(self.dst_dir),
                n_augment=3,
                progress_callback=thread.progress_callback
            )
            
            # シグナルが発行されたか確認
            output_received.assert_called()
            process_finished.assert_called_once_with(0, {
                "original_images": 10,
                "augmented_images": 30,
                "total_images": 40,
                "yaml_file": "test/dataset.yaml"
            })
    
    @pytest.mark.unit
    @pytest.mark.data_augmentation
    @patch('cv2.imread')
    @patch('cv2.imwrite')
    @patch('PIL.Image.open')
    @patch('PIL.Image.Image.save')
    def test_augmentation_variations(self, mock_save, mock_open, mock_imwrite, mock_imread):
        """拡張バリエーション数のテスト"""
        # PILとOpenCVのモック
        mock_img = MagicMock()
        mock_open.return_value = mock_img
        mock_img.size = (640, 480)
        
        # OpenCVのモック
        mock_imread.return_value = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_imwrite.return_value = True
        
        # 異なる拡張数でテスト
        for n_augment in [1, 5, 10]:
            # augment_dataset関数を呼び出す
            result = augment_dataset(
                src_img_dir=str(self.img_dir),
                src_label_dir=str(self.label_dir),
                dst_dir=str(self.dst_dir) + f"_{n_augment}",
                n_augment=n_augment
            )
            
            # 結果が正しいか確認
            self.assertEqual(result["original_images"], 1)  # ダミー画像1枚
            self.assertEqual(result["augmented_images"], n_augment)  # n_augment倍に拡張
            self.assertEqual(result["total_images"], 1 + n_augment)  # 合計


if __name__ == "__main__":
    unittest.main() 