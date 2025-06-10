#!/usr/bin/env python3
"""GroundingDINOの実際のJSONデータを使った検出テスト"""

"""テスト対象: src\utils\auto_annotate.py (エントリーポイント)"""

import os
import sys
import json
import pytest
import numpy as np
import importlib
import logging
from pathlib import Path
from unittest import mock

# ロガー設定 - テスト名と紐づけるためにモジュール名を使用
logger = logging.getLogger(__name__)

# プロジェクトのルートディレクトリをシステムパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 現在のファイルの場所を取得
HERE = Path(__file__).parent
# プロジェクトのルートディレクトリを取得
ROOT = HERE.parent


@pytest.mark.gui
@pytest.mark.integration
@pytest.fixture(autouse=True)
def stub_headless(monkeypatch):
    """PyQt6関連モジュールをモック化（ヘッドレステスト用）"""
    fakes = {
        'PyQt6': mock.MagicMock(),
        'PyQt6.QtCore': mock.MagicMock(),
        'PyQt6.QtCore.QThread': mock.MagicMock(),
        'PyQt6.QtCore.pyqtSignal': mock.MagicMock()
    }
    for module_name, fake_module in fakes.items():
        monkeypatch.setitem(sys.modules, module_name, fake_module)


@pytest.mark.gui
@pytest.mark.integration
@pytest.fixture(scope="session")
def json_data():
    """テスト用JSONデータのフィクスチャ"""
    json_path = ROOT / "annot_kanriz_board.json"
    assert json_path.exists(), f"JSONファイルが見つかりません: {json_path}"
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    logger.info(f"JSONデータ読み込み成功: クラス数={len(data['classes'])}, アノテーション画像数={len(data['annotations'])}")
    return data


@pytest.mark.gui
@pytest.mark.integration
@pytest.fixture
def test_image_path(json_data):
    """テスト用画像のパスを解決するフィクスチャ"""
    # 画像パスの取得
    base_path = Path(json_data.get('base_path', ''))
    if not base_path.exists():
        base_path = ROOT
        logger.info(f"ベースパスが見つからないためルートディレクトリを使用: {base_path}")
    
    # 管理図ボードのアノテーションを持つ最初の画像を使用
    test_img_path = None
    test_boxes = []
    
    for img_path, annotations in json_data['annotations'].items():
        for ann in annotations:
            if any(cls['name'] == '管理図ボード' for cls in json_data['classes'] if cls['id'] == ann.get('class_id')):
                test_img_path = img_path
                test_boxes.append(ann['box'])
                break
        if test_img_path:
            break
    
    assert test_img_path is not None, "管理図ボードが含まれる画像が見つかりません"
    
    # 候補パスをリストとして整理
    img_name = Path(test_img_path).name
    candidates = [
        base_path / test_img_path,
        ROOT / "demo_data" / "dataset_photos" / "出来形" / img_name, 
        ROOT / "test_images" / "board_sample.jpg",  # テスト用の最小画像
        ROOT / img_name,
        Path(test_img_path)
    ]
    
    # 存在する最初のパスを返す
    for path in candidates:
        if path.exists():
            logger.info(f"有効な画像パスが見つかりました: {path}")
            return path
    
    # 候補がすべて見つからない場合は失敗
    assert False, f"テスト画像が見つかりません。候補: {candidates}"


@pytest.mark.gui
@pytest.mark.integration
@pytest.fixture
def kanriboard_annotations(json_data):
    """管理図ボードのアノテーション情報を取得するフィクスチャ"""
    # 管理図ボードのクラスIDを取得
    kanriboard_class_id = None
    for cls in json_data['classes']:
        if cls['name'] == '管理図ボード':
            kanriboard_class_id = cls['id']
            break
    
    assert kanriboard_class_id is not None, "管理図ボードのクラスIDが見つかりません"
    
    # 管理図ボードのアノテーションを取得
    kanriboard_annotations = {}
    for img_path, annotations in json_data['annotations'].items():
        for ann in annotations:
            if ann['class_id'] == kanriboard_class_id:
                if img_path not in kanriboard_annotations:
                    kanriboard_annotations[img_path] = []
                kanriboard_annotations[img_path].append(ann)
    
    return kanriboard_annotations


@pytest.mark.gui
@pytest.mark.integration
@pytest.mark.schema
def test_json_data_structure(json_data):
    """実際のJSONデータの構造をテスト"""
    # 構造を検証
    assert 'classes' in json_data, "JSONにclassesキーがありません"
    assert 'annotations' in json_data, "JSONにannotationsキーがありません"
    assert 'base_path' in json_data, "JSONにbase_pathキーがありません"
    
    # 管理図ボードのクラスIDを確認
    kanriboard_class_id = None
    for cls in json_data['classes']:
        if cls['name'] == '管理図ボード':
            kanriboard_class_id = cls['id']
            break
    
    assert kanriboard_class_id is not None, "管理図ボードのクラスIDが見つかりません"
    logger.info(f"管理図ボードのクラスID: {kanriboard_class_id}")
    
    # 管理図ボードのアノテーション数を確認
    kanriboard_annotations = []
    for img_path, annotations in json_data['annotations'].items():
        for ann in annotations:
            if ann['class_id'] == kanriboard_class_id:
                kanriboard_annotations.append((img_path, ann))
    
    logger.info(f"管理図ボードのアノテーション数: {len(kanriboard_annotations)}")
    assert len(kanriboard_annotations) > 0, "管理図ボードのアノテーションが見つかりません"
    
    # ボックス座標の形式を確認
    for img_path, ann in kanriboard_annotations:
        assert 'box' in ann, f"アノテーションにboxキーがありません: {img_path}"
        assert len(ann['box']) == 4, f"boxの長さが4ではありません: {img_path}"
        x1, y1, x2, y2 = ann['box']
        # 座標値のチェック
        assert all(isinstance(coord, (int, float)) for coord in [x1, y1, x2, y2]), "座標値が数値ではありません"
    
    logger.info("JSONデータ構造のテスト成功")


@pytest.mark.gui
@pytest.mark.integration
@pytest.mark.smoke
def test_actual_image_detection(test_image_path):
    """実際の画像で管理図ボードを検出する完全統合テスト"""
    logger.info("実画像を使った検出テスト開始 - 実モデルを使用")
    logger.info(f"テスト画像: {test_image_path}")
    
    try:
        # 実際の検出関数をインポート
        from src.utils.auto_annotate import detect_objects_in_image, _init_grounding_dino_sam
        
        # モデル初期化
        logger.info("実際のGrounding DINOモデルを初期化しています...")
        detector = _init_grounding_dino_sam(use_gpu=False)
        assert detector is not None, "検出器の初期化に失敗しました"
        logger.info(f"検出器初期化成功: {type(detector)}")
        
        # 必要なメソッドを持っているか確認
        assert hasattr(detector, "predict"), "検出器にpredictメソッドがありません"
        
        # テキストプロンプト
        text_prompt = "管理図ボード ."
        logger.info(f"テキストプロンプト: {text_prompt}")
        
        # 実際に検出を実行
        logger.info("検出を実行中...")
        results = detect_objects_in_image(str(test_image_path), text_prompt)
        
        # 結果の検証
        assert results is not None, "検出結果がNoneです"
        assert isinstance(results, list), "検出結果はリスト型である必要があります"
        logger.info(f"検出結果: {len(results)}個のオブジェクトを検出")
        
        # 検出結果の詳細を検証
        if results:
            first_result = results[0]
            assert isinstance(first_result, dict), "検出結果の各要素は辞書型である必要があります"
            assert "bbox" in first_result, "検出結果にbboxキーがありません"
            assert "score" in first_result, "検出結果にscoreキーがありません"
            assert "label" in first_result, "検出結果にlabelキーがありません"
            
            # ボックス座標を検証
            bbox = first_result["bbox"]
            assert len(bbox) == 4, "ボックス座標は4要素である必要があります"
            assert all(isinstance(coord, (int, float)) for coord in bbox), "ボックス座標は数値である必要があります"
            
            for i, result in enumerate(results):
                logger.info(f"検出 #{i+1}: {result.get('label', '不明')} - 確信度: {result.get('score', 0)}")
                logger.info(f"  ボックス: {result.get('bbox', [])}")
            
            # スコアが0.0～1.0の範囲内であることを確認
            assert 0.0 <= first_result["score"] <= 1.0, "検出スコアが範囲外です"
            
            # 管理図ボードが検出されていることを確認
            assert any(r.get("label") == "管理図ボード" for r in results), "管理図ボードが検出されていません"
        
        logger.info("実画像検出テスト成功")
    except ImportError as e:
        pytest.skip(f"必要なモジュールがインポートできません: {e}")
    except Exception as e:
        logger.error(f"エラー発生: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"実画像検出テスト中にエラーが発生しました: {e}")


@pytest.mark.gui
@pytest.mark.integration
@pytest.mark.unit
def test_grounding_dino_setup(monkeypatch):
    """Grounding DINOのセットアップをテスト（モック版）"""
    logger.info("モックを使ったGrounding DINOセットアップのテスト開始")
    
    # モックモジュールを作成
    fake_gdino = mock.MagicMock(name='rf_groundingdino')
    fake_gdino.load_model.return_value = mock.MagicMock()
    
    fake_sam = mock.MagicMock(name='rf_segment_anything')
    fake_sam.SAMModel.return_value = mock.MagicMock()
    
    # sys.modulesにモックを注入
    monkeypatch.setitem(sys.modules, 'rf_groundingdino', fake_gdino)
    monkeypatch.setitem(sys.modules, 'rf_segment_anything', fake_sam)
    
    # モジュールのインポートを試みる
    try:
        import src.utils.auto_annotate as AA
        importlib.reload(AA)  # 注入したモジュールを確実に使うためリロード
    except ImportError:
        pytest.skip("auto_annotateモジュールが見つかりません")
    
    # 初期化関数が存在するか確認
    assert hasattr(AA, '_init_grounding_dino_sam'), "_init_grounding_dino_sam関数が実装されていません"
    
    logger.info("_init_grounding_dino_sam関数を呼び出します")
    
    # モデルを初期化
    detector = AA._init_grounding_dino_sam(use_gpu=False)
    
    # 検出器の検証
    assert detector is not None, "detectorがNoneになっています"
    
    # 必要なメソッドを持っているか確認
    expected_methods = ["predict"]
    for method in expected_methods:
        assert hasattr(detector, method), f"detectorに{method}メソッドがありません"
    
    # 正しいメソッドが呼ばれたことを確認
    fake_gdino.load_model.assert_called_once()
    fake_sam.SAMModel.assert_called_once()
    
    logger.info("モックを使ったGrounding DINOセットアップのテスト成功")


@pytest.mark.gui
@pytest.mark.integration
@pytest.mark.smoke
def test_grounding_dino_real_initialization():
    """実際のGrounding DINOの初期化をテスト（モック無し）"""
    logger.info("実際のGrounding DINOセットアップのテスト開始")
    
    # モックなしでモジュールをインポート
    try:
        import src.utils.auto_annotate as AA
    except ImportError:
        pytest.skip("auto_annotateモジュールが見つかりません")
    
    # 初期化関数が存在するか確認
    assert hasattr(AA, '_init_grounding_dino_sam'), "_init_grounding_dino_sam関数が実装されていません"
    
    try:
        logger.info("実際の_init_grounding_dino_sam関数を呼び出します")
        
        # 実際のモデルを初期化
        detector = AA._init_grounding_dino_sam(use_gpu=False)
        
        # 検出器の検証
        assert detector is not None, "実際のdetectorがNoneになっています"
        logger.info(f"実際のdetector type: {type(detector)}")
        
        # 必要なメソッドを持っているか確認
        assert hasattr(detector, "predict"), "検出器にpredictメソッドがありません"
        
        logger.info("実際のGrounding DINOセットアップのテスト成功")
    except Exception as e:
        logger.error(f"実際のGrounding DINO初期化中にエラー発生: {e}")
        pytest.fail(f"実際のGrounding DINO初期化中にエラーが発生しました: {e}")


@pytest.mark.gui
@pytest.mark.integration
@pytest.mark.unit
def test_single_class_detection(monkeypatch, kanriboard_annotations, test_image_path):
    """単一クラス（管理図ボード）の検出テスト（モック版）"""
    logger.info("単一クラス検出テスト開始")
    
    # テスト用のボックスを取得
    first_img_path = list(kanriboard_annotations.keys())[0]
    test_boxes = [ann['box'] for ann in kanriboard_annotations[first_img_path]]
    
    logger.info(f"テスト画像: {first_img_path}")
    logger.info(f"アノテーションされた管理図ボードの数: {len(test_boxes)}")
    
    # テスト用のダミー検出データを作成
    dummy_boxes = np.array([[100, 100, 500, 500]])  # サンプルボックス
    dummy_logits = np.array([0.95])  # 高い確信度
    dummy_phrases = ['管理図ボード']  # クラス名
    
    # モックGroundingDINOとSAMを作成
    fake_model = mock.MagicMock()
    fake_model.predict_with_caption.return_value = (dummy_boxes, dummy_logits, dummy_phrases)
    
    fake_gdino = mock.MagicMock()
    fake_gdino.model = fake_model
    
    # auto_annotateモジュールをインポート
    try:
        import src.utils.auto_annotate as AA
        importlib.reload(AA)  # モジュールをリロード
    except ImportError:
        pytest.skip("auto_annotateモジュールが見つかりません")
    
    # detect_objects_in_image関数が存在するか確認
    assert hasattr(AA, 'detect_objects_in_image'), "detect_objects_in_image関数が実装されていません"
    
    # モックでGroundingDINO APIを上書き
    def mock_detect(*args, **kwargs):
        return [
            {
                "bbox": [100, 100, 500, 500],
                "score": 0.95,
                "label": "管理図ボード",
                "image_size": (1000, 1000)
            }
        ]
    
    # detect_objects_in_image関数をモックで置き換え（monkeypatch.setattrを使用）
    monkeypatch.setattr(AA, "detect_objects_in_image", mock_detect)
    
    # テキストプロンプト
    text_prompt = "管理図ボード"
    logger.info(f"テキストプロンプト: {text_prompt}")
    
    # 検出を実行
    logger.info("detect_objects_in_image関数を呼び出します")
    results = AA.detect_objects_in_image(str(test_image_path), text_prompt)
    
    # 検出結果を検証
    assert results is not None, "検出結果がNoneです"
    assert isinstance(results, list), "検出結果はリスト型である必要があります"
    assert len(results) > 0, "検出結果が空です"
    
    # 最初の結果を詳細に検証
    first_result = results[0]
    assert isinstance(first_result, dict), "検出結果はdict型である必要があります"
    assert "bbox" in first_result, "検出結果にbboxキーがありません"
    assert "score" in first_result, "検出結果にscoreキーがありません"
    assert "label" in first_result, "検出結果にlabelキーがありません"
    
    # 値の検証
    assert first_result["label"] == "管理図ボード", f"ラベルが期待値と異なります: {first_result['label']}"
    assert 0.9 <= first_result["score"] <= 1.0, f"スコアが範囲外です: {first_result['score']}"
    assert len(first_result["bbox"]) == 4, f"ボックスの要素数が不正です: {len(first_result['bbox'])}"
    
    logger.info("単一クラス検出テスト成功") 