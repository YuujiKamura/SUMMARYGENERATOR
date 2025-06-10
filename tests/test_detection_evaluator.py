#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
検出評価ツールのテスト
"""

"""テスト対象: src\utils\detection_evaluator.py (バックエンドモジュール)"""
import os
import sys
import json
import pytest
import logging
import numpy as np
import tempfile
from pathlib import Path
from unittest import mock
import cv2

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# テスト対象のモジュールをインポート
from src.utils.detection_evaluator import DetectionEvaluator

# ロガー設定
logger = logging.getLogger(__name__)


@pytest.fixture
def mock_detector():
    """モック検出器を作成するフィクスチャ"""
    detector = mock.MagicMock()
    detector.predict.return_value = (
        np.array([[100, 100, 200, 200]]),  # ボックス
        np.array([0.95]),  # スコア
        ['管理図ボード']  # ラベル
    )
    return detector


@pytest.fixture
def temp_json_path():
    """テスト用の一時JSONファイルを作成するフィクスチャ"""
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        # テスト用のダミーJSONデータ
        data = {
            "base_path": str(Path(__file__).parent),
            "classes": [
                {"id": 1, "name": "管理図ボード"},
                {"id": 2, "name": "作業員"}
            ],
            "annotations": {
                "test_image.jpg": [
                    {"class_id": 1, "box": [90, 90, 210, 210]},
                    {"class_id": 2, "box": [300, 300, 400, 400]}
                ]
            }
        }
        f.write(json.dumps(data).encode('utf-8'))
    
    yield Path(f.name)
    
    # テスト後に削除
    os.unlink(f.name)


@pytest.fixture
def temp_image_path():
    """テスト用の一時画像ファイルを作成するフィクスチャ"""
    # テスト用の画像ディレクトリ
    img_dir = Path(__file__).parent
    img_path = img_dir / "test_image.jpg"
    
    # 画像が存在しない場合は作成
    if not img_path.exists():
        try:
            # テスト画像作成 (白背景に黒い四角)
            img = np.ones((500, 500, 3), dtype=np.uint8) * 255
            # 管理図ボード用の四角（左上）
            cv2.rectangle(img, (90, 90), (210, 210), (0, 0, 0), -1)
            # 作業員用の四角（右下）
            cv2.rectangle(img, (300, 300), (400, 400), (0, 0, 0), -1)
            cv2.imwrite(str(img_path), img)
        except ImportError:
            logger.warning("cv2がインストールされていないため、テスト画像を作成できません")
            pytest.skip("cv2がインストールされていません")
    
    yield img_path
    
    # テスト後に削除
    if img_path.exists():
        os.unlink(img_path)


@pytest.mark.unit
@pytest.mark.smoke
def test_evaluator_initialization(temp_json_path):
    """評価ツールの初期化テスト"""
    # DetectionEvaluatorの_init_grounding_dino_samをモックに置き換え
    with mock.patch('src.utils.detection_evaluator._init_grounding_dino_sam') as mock_init:
        mock_init.return_value = mock.MagicMock()
        
        # 評価ツールを初期化
        evaluator = DetectionEvaluator(
            json_path=temp_json_path,
            class_names=['管理図ボード']
        )
        
        # 初期化が正しく行われたことを確認
        assert evaluator.json_path == temp_json_path
        assert evaluator.class_names == ['管理図ボード']
        assert evaluator.iou_threshold == 0.5  # デフォルト値
        assert mock_init.called


@pytest.mark.unit
def test_load_json(temp_json_path):
    """JSONファイル読み込みテスト"""
    # DetectionEvaluatorの_init_grounding_dino_samをモックに置き換え
    with mock.patch('src.utils.detection_evaluator._init_grounding_dino_sam') as mock_init:
        mock_init.return_value = mock.MagicMock()
        
        # 評価ツールを初期化
        evaluator = DetectionEvaluator(
            json_path=temp_json_path,
            class_names=['管理図ボード']
        )
        
        # JSONデータが正しく読み込まれていることを確認
        assert '管理図ボード' in evaluator.class_ids
        assert evaluator.class_ids['管理図ボード'] == 1
        assert evaluator.class_mapping[1] == '管理図ボード'
        assert len(evaluator.data['annotations']) == 1
        assert 'test_image.jpg' in evaluator.data['annotations']


@pytest.mark.unit
@pytest.mark.smoke
def test_calculate_iou(temp_json_path):
    """IoU計算テスト"""
    # DetectionEvaluatorの_init_grounding_dino_samをモックに置き換え
    with mock.patch('src.utils.detection_evaluator._init_grounding_dino_sam') as mock_init:
        mock_init.return_value = mock.MagicMock()
        
        # 評価ツールを初期化
        evaluator = DetectionEvaluator(
            json_path=temp_json_path,
            class_names=['管理図ボード']
        )
        
        # IoU計算テスト
        # 完全一致 (IoU = 1.0)
        box_a = [100, 100, 200, 200]
        box_b = [100, 100, 200, 200]
        iou = evaluator._calculate_iou(box_a, box_b)
        assert pytest.approx(iou, abs=1e-5) == 1.0
        
        # 完全に外れている (IoU = 0.0)
        box_a = [100, 100, 200, 200]
        box_b = [300, 300, 400, 400]
        iou = evaluator._calculate_iou(box_a, box_b)
        assert pytest.approx(iou, abs=1e-5) == 0.0
        
        # 部分的に重なっている
        box_a = [100, 100, 200, 200]
        box_b = [150, 150, 250, 250]
        iou = evaluator._calculate_iou(box_a, box_b)
        # 重なり領域: 50x50 = 2500
        # box_a面積: 100x100 = 10000
        # box_b面積: 100x100 = 10000
        # 合計面積 - 重なり: 10000 + 10000 - 2500 = 17500
        # IoU = 2500 / 17500 = 0.1429
        assert pytest.approx(iou, abs=1e-3) == 0.1429


@pytest.mark.unit
def test_evaluate_detections(temp_json_path):
    """検出評価のロジックテスト"""
    # DetectionEvaluatorの_init_grounding_dino_samをモックに置き換え
    with mock.patch('src.utils.detection_evaluator._init_grounding_dino_sam') as mock_init:
        mock_init.return_value = mock.MagicMock()
        
        # 評価ツールを初期化
        evaluator = DetectionEvaluator(
            json_path=temp_json_path,
            class_names=['管理図ボード']
        )
        
        # 検出結果の評価用データを準備
        cls_name = "管理図ボード"
        evaluator.results = {cls_name: {
            'true_positives': 0,
            'false_positives': 0,
            'false_negatives': 0,
            'iou_values': []
        }}
        
        # ケース1: 検出結果とGTが一致する場合 (True Positive)
        detections = [{'bbox': [100, 100, 200, 200], 'score': 0.95, 'label': cls_name}]
        gt_boxes = [[100, 100, 200, 200]]
        evaluator._evaluate_detections(cls_name, detections, gt_boxes)
        assert evaluator.results[cls_name]['true_positives'] == 1
        assert evaluator.results[cls_name]['false_positives'] == 0
        assert evaluator.results[cls_name]['false_negatives'] == 0
        
        # 結果をリセット
        evaluator.results[cls_name] = {
            'true_positives': 0,
            'false_positives': 0,
            'false_negatives': 0,
            'iou_values': []
        }
        
        # ケース2: 検出結果なしでGTがある場合 (False Negative)
        detections = []
        gt_boxes = [[100, 100, 200, 200]]
        evaluator._evaluate_detections(cls_name, detections, gt_boxes)
        assert evaluator.results[cls_name]['true_positives'] == 0
        assert evaluator.results[cls_name]['false_positives'] == 0
        assert evaluator.results[cls_name]['false_negatives'] == 1
        
        # 結果をリセット
        evaluator.results[cls_name] = {
            'true_positives': 0,
            'false_positives': 0,
            'false_negatives': 0,
            'iou_values': []
        }
        
        # ケース3: 検出結果ありでGTがない場合 (False Positive)
        detections = [{'bbox': [100, 100, 200, 200], 'score': 0.95, 'label': cls_name}]
        gt_boxes = []
        evaluator._evaluate_detections(cls_name, detections, gt_boxes)
        assert evaluator.results[cls_name]['true_positives'] == 0
        assert evaluator.results[cls_name]['false_positives'] == 1
        assert evaluator.results[cls_name]['false_negatives'] == 0


@pytest.mark.unit
def test_detect_objects(temp_json_path):
    """オブジェクト検出関数のテスト"""
    # detect_objects_in_imageをモックに置き換え
    with mock.patch('src.utils.detection_evaluator.detect_objects_in_image') as mock_detect:
        # モックの戻り値を設定
        mock_detect.return_value = [
            {'bbox': [100, 100, 200, 200], 'score': 0.95, 'label': '管理図ボード'}
        ]
        
        # DetectionEvaluatorの_init_grounding_dino_samもモックに置き換え
        with mock.patch('src.utils.detection_evaluator._init_grounding_dino_sam') as mock_init:
            mock_init.return_value = mock.MagicMock()
            
            # 評価ツールを初期化
            evaluator = DetectionEvaluator(
                json_path=temp_json_path,
                class_names=['管理図ボード']
            )
            
            # 検出実行
            detections = evaluator._detect_objects('test_image.jpg', '管理図ボード')
            
            # 結果を確認
            assert len(detections) == 1
            assert detections[0]['bbox'] == [100, 100, 200, 200]
            assert detections[0]['score'] == 0.95
            assert detections[0]['label'] == '管理図ボード'


@pytest.mark.integration
def test_evaluate_image(temp_json_path, temp_image_path):
    """画像評価のテスト（モックを使用）"""
    # detect_objects_in_imageをモックに置き換え
    with mock.patch('src.utils.detection_evaluator.detect_objects_in_image') as mock_detect:
        
        # モックの戻り値を設定（管理図ボードの検出結果）
        mock_detect.return_value = [
            {'bbox': [90, 90, 210, 210], 'score': 0.95, 'label': '管理図ボード'}
        ]
        
        # DetectionEvaluatorの_init_grounding_dino_samもモックに置き換え
        with mock.patch('src.utils.detection_evaluator._init_grounding_dino_sam') as mock_init:
            
            mock_init.return_value = mock.MagicMock()
            
            # 評価ツールを初期化
            evaluator = DetectionEvaluator(
                json_path=temp_json_path,
                class_names=['管理図ボード']
            )
            
            # 1枚の画像を評価
            evaluator.results = {'管理図ボード': {
                'true_positives': 0,
                'false_positives': 0,
                'false_negatives': 0,
                'iou_values': []
            }}
            results = evaluator.evaluate_image('test_image.jpg', evaluator.data['annotations']['test_image.jpg'])
            
            # 評価後の結果を確認（evaluator.resultsを検証）
            assert evaluator.results['管理図ボード']['true_positives'] == 1
            assert evaluator.results['管理図ボード']['false_positives'] == 0
            
            # 検出結果も確認（resultsにはリスト形式で検出結果が含まれる）
            assert isinstance(results, dict)
            assert '管理図ボード' in results
            assert isinstance(results['管理図ボード'], list)
            assert len(results['管理図ボード']) == 1
            assert results['管理図ボード'][0]['bbox'] == [90, 90, 210, 210]


@pytest.mark.integration
def test_calculate_metrics(temp_json_path):
    """メトリクス計算のテスト"""
    # DetectionEvaluatorの_init_grounding_dino_samをモックに置き換え
    with mock.patch('src.utils.detection_evaluator._init_grounding_dino_sam') as mock_init:
        mock_init.return_value = mock.MagicMock()
        
        # 評価ツールを初期化
        evaluator = DetectionEvaluator(
            json_path=temp_json_path,
            class_names=['管理図ボード', '作業員']
        )
        
        # テストデータを設定
        evaluator.results = {
            '管理図ボード': {
                'true_positives': 8,
                'false_positives': 2,
                'false_negatives': 1,
                'iou_values': [0.8, 0.9, 0.85, 0.95, 0.75, 0.8, 0.85, 0.9]
            },
            '作業員': {
                'true_positives': 6,
                'false_positives': 1,
                'false_negatives': 2,
                'iou_values': [0.85, 0.9, 0.8, 0.95, 0.85, 0.9]
            }
        }
        
        # メトリクスを計算
        evaluator._calculate_metrics()
        
        # 結果を確認
        assert evaluator.metrics['per_class']['管理図ボード']['precision'] == pytest.approx(0.8, abs=1e-5)  # 8 / (8 + 2)
        assert evaluator.metrics['per_class']['管理図ボード']['recall'] == pytest.approx(0.889, abs=1e-3)  # 8 / (8 + 1)
        assert evaluator.metrics['per_class']['管理図ボード']['f1_score'] == pytest.approx(0.842, abs=1e-3)
        assert evaluator.metrics['per_class']['管理図ボード']['mean_iou'] == pytest.approx(0.85, abs=1e-5)
        
        assert evaluator.metrics['per_class']['作業員']['precision'] == pytest.approx(0.857, abs=1e-3)  # 6 / (6 + 1)
        assert evaluator.metrics['per_class']['作業員']['recall'] == pytest.approx(0.75, abs=1e-5)  # 6 / (6 + 2)
        assert evaluator.metrics['per_class']['作業員']['f1_score'] == pytest.approx(0.8, abs=1e-5)
        assert evaluator.metrics['per_class']['作業員']['mean_iou'] == pytest.approx(0.875, abs=1e-3)
        
        assert evaluator.metrics['overall']['precision'] == pytest.approx(0.824, abs=1e-3)  # (8 + 6) / (10 + 7)
        assert evaluator.metrics['overall']['recall'] == pytest.approx(0.824, abs=1e-3)  # (8 + 6) / (9 + 8)
        assert evaluator.metrics['overall']['f1_score'] == pytest.approx(0.824, abs=1e-3)
        assert evaluator.metrics['overall']['mean_iou'] == pytest.approx(0.86, abs=1e-2) 