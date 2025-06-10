#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Grounding DINOとSAMのモデル初期化スモークテスト
"""
import os
import sys
import pytest
import logging
import time
from pathlib import Path

# ロガー設定
logger = logging.getLogger(__name__)

# プロジェクトのルートディレクトリをシステムパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# モデル初期化のタイムアウト時間（秒）
MODEL_INIT_TIMEOUT = 60


@pytest.mark.smoke
def test_model_initialization():
    """実際のGrounding DINO + SAMモデルを初期化するテスト"""
    logger.info("Grounding DINO + SAMモデル初期化のスモークテスト開始")
    
    try:
        # 初期化関数をインポート
        from src.utils.auto_annotate import _init_grounding_dino_sam
        
        # モデルを初期化（GPUなし、軽量モード）
        logger.info("モデルを初期化中...")
        
        # タイムアウト対策
        start_time = time.time()
        
        try:
            detector = _init_grounding_dino_sam(use_gpu=False)
            
            # タイムアウトチェック
            elapsed_time = time.time() - start_time
            if elapsed_time > MODEL_INIT_TIMEOUT:
                logger.warning(f"モデル初期化に時間がかかりすぎています: {elapsed_time:.2f}秒 > {MODEL_INIT_TIMEOUT}秒")
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"モデル初期化中にエラーが発生 ({elapsed_time:.2f}秒): {e}")
            pytest.fail(f"モデル初期化中にエラーが発生しました: {e}")
        
        # 検出器の検証
        assert detector is not None, "モデル初期化でNoneが返されました"
        logger.info(f"モデル初期化成功: {type(detector)}")
        
        # 必要なメソッドを持っているか確認
        assert hasattr(detector, "predict"), "検出器にpredictメソッドがありません"
        
        # メモリリークを防ぐためのクリーンアップ
        detector = None
        
        logger.info("モデル初期化スモークテスト成功")
    except ImportError as e:
        pytest.skip(f"必要なモジュールがインポートできません: {e}")
    except Exception as e:
        logger.error(f"モデル初期化中にエラーが発生: {e}")
        pytest.fail(f"モデル初期化テスト中にエラーが発生しました: {e}")


if __name__ == "__main__":
    # 直接実行時のテスト用
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # テスト実行
    test_model_initialization() 