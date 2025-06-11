#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
テストユーティリティ関数
"""
import os
import sys
import time
import logging
import numpy as np
from pathlib import Path
from typing import Optional, List, Dict, Any, Union, Callable
import unicodedata

from PyQt6.QtCore import QCoreApplication, QTimer

# ロガー設定
logger = logging.getLogger(__name__)

# ルートディレクトリの取得
ROOT = Path(__file__).parent.parent


def wait_for_processing(timeout_ms: int = 5000, check_condition: Optional[Callable[[], bool]] = None) -> bool:
    """処理が完了するまで待機する関数
    
    Args:
        timeout_ms: タイムアウト時間（ミリ秒）
        check_condition: 条件チェック関数（Noneの場合は時間だけ待機）
        
    Returns:
        bool: 条件が満たされた場合はTrue、タイムアウトした場合はFalse
    """
    start_time = time.time()
    timeout_sec = timeout_ms / 1000.0
    
    # 条件関数が指定されていない場合は単にイベントループを回す
    if check_condition is None:
        # シンプルなタイマーによる待機
        waiting = True
        def stop_waiting():
            nonlocal waiting
            waiting = False
        
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(stop_waiting)
        timer.start(timeout_ms)
        
        while waiting:
            QCoreApplication.processEvents()
            time.sleep(0.01)
        
        return True
    
    # 条件関数が指定されている場合は条件を満たすまで待機
    while time.time() - start_time < timeout_sec:
        QCoreApplication.processEvents()
        
        # 条件チェック
        if check_condition():
            return True
        
        # 短時間スリープしてCPU使用率を下げる
        time.sleep(0.01)
    
    # タイムアウト
    logger.warning(f"処理がタイムアウトしました（{timeout_ms}ms）")
    return False


def resolve_test_image(
    json_data: Dict[str, Any] = None,
    cls_name: str = "管理図ボード",
    fallback_names: List[str] = None
) -> Path:
    """テスト用画像のパスを解決するユーティリティ関数

    Args:
        json_data: JSONデータ（アノテーション情報を含む）
        cls_name: 対象のクラス名
        fallback_names: フォールバック用の画像名リスト

    Returns:
        解決されたパス
    """
    # 基本パスの設定
    if json_data and 'base_path' in json_data:
        base_path = Path(json_data.get('base_path', ''))
        if not base_path.exists():
            base_path = ROOT
            logger.info(f"ベースパスが見つからないためルートディレクトリを使用: {base_path}")
    else:
        base_path = ROOT
    
    # 候補画像パスのリスト
    candidates = []
    
    # JSONデータからクラス名に一致するアノテーションを持つ画像を探す
    if json_data and 'annotations' in json_data and 'classes' in json_data:
        # クラスIDを取得
        class_id = None
        for cls in json_data['classes']:
            if cls['name'] == cls_name:
                class_id = cls['id']
                break
        
        # クラスIDに一致するアノテーションを持つ画像を探す
        if class_id is not None:
            for img_path, annotations in json_data['annotations'].items():
                for ann in annotations:
                    if ann.get('class_id') == class_id:
                        img_name = Path(img_path).name
                        candidates.append((base_path / img_path, f"JSONから検出: {img_name}"))
                        break
    
    # フォールバック用の候補パスを追加
    if not candidates or not any(path.exists() for path, _ in candidates):
        # フォールバック名が指定されていない場合はデフォルト値を使用
        if fallback_names is None:
            fallback_names = ["board_sample.jpg", "test_board.jpg", "sample.jpg"]
        
        # デモデータディレクトリなどを探索
        for name in fallback_names:
            candidates.extend([
                (ROOT / "test_images" / name, f"テスト画像: {name}"),
                (ROOT / "demo_data" / name, f"デモデータ: {name}"),
                (ROOT / "demo_data" / "dataset_photos" / "出来形" / name, f"出来形データ: {name}"),
                (ROOT / name, f"ルート: {name}")
            ])
    
    # 有効なパスを探す
    for path, desc in candidates:
        if path.exists():
            logger.info(f"有効な画像パスが見つかりました [{desc}]: {path}")
            return path
    
    # どの候補も見つからない場合は合成画像を返す
    logger.warning(f"有効な画像パスが見つかりませんでした。候補: {[str(p) for p, _ in candidates]}")
    logger.info("テスト用の合成画像を生成します")
    return create_dummy_test_image()


def create_dummy_test_image(
    output_dir: Optional[Path] = None,
    width: int = 640,
    height: int = 480
) -> Path:
    """テスト用のダミー画像を生成する

    Args:
        output_dir: 出力ディレクトリ（Noneの場合はテンポラリディレクトリを使用）
        width: 画像の幅
        height: 画像の高さ

    Returns:
        生成された画像のパス
    """
    try:
        import cv2
        import tempfile
        
        # 出力ディレクトリの設定
        if output_dir is None:
            output_dir = Path(tempfile.gettempdir())
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # ダミー画像の生成（白背景に黒い四角）
        img = np.ones((height, width, 3), dtype=np.uint8) * 255
        # 中央に黒い四角を描画（疑似的な管理図ボード）
        x1, y1 = width // 4, height // 4
        x2, y2 = width * 3 // 4, height * 3 // 4
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 0), -1)
        
        # 画像の保存
        output_path = output_dir / "dummy_test_board.jpg"
        cv2.imwrite(str(output_path), img)
        
        logger.info(f"ダミーテスト画像を生成しました: {output_path}")
        return output_path
    
    except ImportError:
        logger.error("cv2がインストールされていないため、ダミー画像を生成できません")
        raise 

def get_display_width(text):
    width = 0
    for c in str(text):
        if unicodedata.east_asian_width(c) in ('F', 'W', 'A'):
            width += 2
        else:
            width += 1
    return width

def pad_display(text, width):
    pad_len = width - get_display_width(text)
    return str(text) + ' ' * pad_len

def print_aligned_pairs(pairs_dict, keys=None, label_prefix='  ', sep=' : '):
    """
    pairs_dict: {ラベル: 値} の辞書
    keys: 出力順を指定したい場合のラベルリスト
    label_prefix: ラベルの前に付ける文字列
    sep: ラベルと値の区切り
    """
    if keys is None:
        keys = list(pairs_dict.keys())
    max_label_width = max(get_display_width(k) for k in keys)
    for k in keys:
        v = pairs_dict.get(k)
        print(f"{label_prefix}{pad_display(k, max_label_width)}{sep}{v}")

def setup_qt_test_environment():
    """Qtテスト環境をセットアップ"""
    import os
    import sys
    from PyQt6.QtWidgets import QApplication
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["QT_LOGGING_TO_CONSOLE"] = "0"
    os.environ["QT_FORCE_HEADLESS"] = "1"
    if not QApplication.instance():
        try:
            app = QApplication(sys.argv)
            return True
        except Exception as e:
            print(f"Qt環境のセットアップに失敗: {e}")
            return False
    return True