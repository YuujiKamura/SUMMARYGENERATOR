import os
from typing import Optional
from src.yolo_dataset_exporter import YoloDatasetExporter
from src.utils.data_augmenter import augment_dataset

def convert_image_to_yolo_dataset(json_path: str, output_dir: Optional[str] = None, val_ratio: float = 0.0, force_flush: bool = True) -> dict:
    """
    個別画像JSONをYOLOデータセットに変換する
    Args:
        json_path: 画像リストJSONのパス（1ファイル）
        output_dir: 出力先ディレクトリ
        val_ratio: 検証用分割比率（単体変換時は0.0推奨）
        force_flush: 出力先をクリーン再生成するか
    Returns:
        dict: 変換結果サマリー
    """
    exporter = YoloDatasetExporter([json_path], output_dir=output_dir, val_ratio=val_ratio)
    result = exporter.export(mode='all', force_flush=force_flush)
    return result

def augment_image_dataset(src_img_dir: str, src_label_dir: str, dst_dir: str, n_augment: int = 5) -> dict:
    """
    YOLOデータセットの画像・ラベルディレクトリを拡張し、新しいデータセットを生成する
    Args:
        src_img_dir: 元画像ディレクトリ
        src_label_dir: 元ラベルディレクトリ
        dst_dir: 拡張後の出力ディレクトリ
        n_augment: 画像ごとの拡張数
    Returns:
        dict: 拡張処理の結果情報
    """
    result = augment_dataset(
        src_img_dir=src_img_dir,
        src_label_dir=src_label_dir,
        dst_dir=dst_dir,
        n_augment=n_augment
    )
    return result 