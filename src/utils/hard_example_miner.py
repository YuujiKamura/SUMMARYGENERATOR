from __future__ import annotations

"""hard_example_miner.py

YOLO で学習したモデルを使ってデータセット全画像を推論し、
予測結果と GT(ground truth) ラベルを比較して食い違いのある画像（ミス検出）
だけを抽出するユーティリティ。

抽出した画像とラベルは YOLO 形式のディレクトリ構造
    output_dir/images/...
    output_dir/labels/...
にコピーされる。

Usage::

    from src.utils.hard_example_miner import collect_mis_detect_images
    n = collect_mis_detect_images(model_path, dataset_dir, output_dir)

戻り値は抽出された画像数。
"""

from pathlib import Path
import shutil
from typing import List

import yaml  # type: ignore
from tqdm import tqdm

try:
    from ultralytics import YOLO
except ImportError as e:  # pragma: no cover
    raise ImportError("ultralytics パッケージが必要です: pip install ultralytics") from e

__all__ = ["collect_mis_detect_images", "generate_dataset_yaml"]


def _normalize_label_lines(path: Path) -> List[str]:
    """YOLO ラベルファイルを読み込み、conf スコアを除去して比較用に正規化。"""
    if not path.exists():
        return []
    lines: List[str] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split()
            if not parts:
                continue
            # conf スコア列を削除 (先頭5列が class cx cy w h)
            lines.append(" ".join(parts[:5]))
    return lines


def collect_mis_detect_images(
    model_path: str | Path,
    dataset_dir: str | Path,
    output_dir: str | Path,
    conf: float = 0.25,
    iou: float = 0.5,
) -> int:
    """データセット全画像に対し推論し、GT と食い違う画像を output_dir にコピーする。

    Parameters
    ----------
    model_path: str | Path
        学習済み YOLO モデル (.pt ファイル)
    dataset_dir: str | Path
        YOLO データセットルート (data.yaml があるディレクトリ)
    output_dir: str | Path
        ミス検出画像を出力するディレクトリ
    conf: float, default 0.25
        推論時の信頼度閾値
    iou: float, default 0.5
        NMS の IoU 閾値  (現状は単純 diff 比較なので未使用だが将来的拡張に備える)

    Returns
    -------
    int
        抽出された画像数 (ミス検出画像数)
    """
    model_path = Path(model_path)
    dataset_dir = Path(dataset_dir)
    output_dir = Path(output_dir)

    output_images_dir = output_dir / "images" / "train"
    output_labels_dir = output_dir / "labels" / "train"
    output_images_dir.mkdir(parents=True, exist_ok=True)
    output_labels_dir.mkdir(parents=True, exist_ok=True)

    # ------------- 推論実行 -------------
    model = YOLO(str(model_path))

    images_root = dataset_dir / "images"
    img_paths = sorted([p for p in images_root.rglob("*.*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"}])
    if not img_paths:
        raise ValueError(f"画像が見つかりません: {images_root}")

    # Ultralytics の predict は大量に画像を渡すとメモリを食うので分割
    batch_size = 128
    pred_label_root: Path | None = None
    for i in range(0, len(img_paths), batch_size):
        batch = img_paths[i : i + batch_size]
        results = model.predict(
            [str(p) for p in batch],
            save_txt=True,
            save_conf=True,
            conf=conf,
            iou=iou,
            project=str(output_dir),  # 同じ出力先でも exist_ok=True なら上書きマージされる
            name="_tmp_predict",
            exist_ok=True,
            verbose=False,
        )
        # 保存先ディレクトリを 1 回だけ取得
        if pred_label_root is None and results:
            pred_label_root = Path(results[0].save_dir) / "labels"

    if pred_label_root is None or not pred_label_root.exists():
        raise RuntimeError("予測ラベルの保存先が見つかりません")

    # ------------- GT と比較 -------------
    mis_count = 0
    gt_labels_root = dataset_dir / "labels"

    for img_path in tqdm(img_paths, desc="hard-example mining"):
        rel = img_path.relative_to(images_root)
        gt_label_path = gt_labels_root / rel.with_suffix(".txt")
        pred_label_path = pred_label_root / rel.with_suffix(".txt")

        gt_lines = _normalize_label_lines(gt_label_path)
        pred_lines = _normalize_label_lines(pred_label_path)

        if set(gt_lines) != set(pred_lines):
            # 食い違い画像をコピー
            dst_img = output_images_dir / rel
            dst_lbl = output_labels_dir / rel.with_suffix(".txt")
            dst_img.parent.mkdir(parents=True, exist_ok=True)
            dst_lbl.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(img_path, dst_img)
            if gt_label_path.exists():
                shutil.copy2(gt_label_path, dst_lbl)
            mis_count += 1

    # ------------- data.yaml 生成 -------------
    if mis_count:
        generate_dataset_yaml(output_dir, reference_dataset_dir=dataset_dir)

    # 一時 predict ディレクトリを削除
    shutil.rmtree(pred_label_root.parent.parent, ignore_errors=True)  # runs/detect/_tmp_predict

    return mis_count


def generate_dataset_yaml(dataset_root: str | Path, reference_dataset_dir: str | Path | None = None) -> Path:
    """dataset_root 配下に data.yaml を生成して返す。

    reference_dataset_dir が与えられた場合は、その data.yaml から
    nc / names を引き継いで設定する。
    """
    dataset_root = Path(dataset_root)
    yaml_path = dataset_root / "data.yaml"

    nc = 999
    names: list[str] = []

    if reference_dataset_dir:
        ref_yaml_path = Path(reference_dataset_dir) / "data.yaml"
        if ref_yaml_path.exists():
            try:
                with ref_yaml_path.open("r", encoding="utf-8") as f:
                    ref_data = yaml.safe_load(f)
                nc = ref_data.get("nc", nc)
                names = ref_data.get("names", names)
            except Exception:  # pragma: no cover
                pass

    data = {
        "path": str(dataset_root),
        "train": "images/train",
        "val": "images/train",  # ミス画像を train/val 共用
        "nc": nc,
        "names": names,
    }
    with yaml_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    return yaml_path
