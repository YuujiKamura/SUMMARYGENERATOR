import os
from pathlib import Path
import yaml
from src.yolo_dataset_exporter import YoloDatasetExporter
from src.utils.data_augmenter import augment_dataset

def run_yolo_e2e_pipeline(
    scan_json,
    model_path,
    epochs=5,
    n_augment=2,
    output_dir=None,
    progress_callback=print
):
    """
    scan_jsonからYOLOデータセット生成→拡張→学習まで一括実行する共通関数。
    テスト・GUI両方から呼び出し可能。
    """
    scan_json = Path(scan_json)
    if output_dir is None:
        output_dir = scan_json.parent / "yolo_e2e_output"
    output_dir = Path(output_dir)
    # 1. YOLOデータセット生成
    progress_callback(f"[E2E] YOLOデータセット生成: {scan_json} → {output_dir}")
    exporter = YoloDatasetExporter([str(scan_json)], output_dir=str(output_dir), val_ratio=0.1)
    export_result = exporter.export(force_flush=True)
    dataset_yaml = output_dir / "dataset.yaml"
    if not dataset_yaml.exists():
        raise FileNotFoundError(f"dataset.yamlが生成されませんでした: {dataset_yaml}")
    # 2. データ拡張
    progress_callback(f"[E2E] データ拡張: n_augment={n_augment}")
    images_dir = output_dir / "images" / "train"
    labels_dir = output_dir / "labels" / "train"
    aug_out_dir = output_dir.parent / "augmented_dataset"
    result = augment_dataset(
        src_img_dir=str(images_dir),
        src_label_dir=str(labels_dir),
        dst_dir=str(aug_out_dir),
        n_augment=n_augment
    )
    aug_yaml = Path(result.get('yaml_file', aug_out_dir / "dataset.yaml"))
    if not aug_yaml.exists():
        raise FileNotFoundError(f"拡張後dataset.yamlが生成されませんでした: {aug_yaml}")
    # 3. YOLO学習
    progress_callback(f"[E2E] YOLO学習開始: data={aug_yaml} model={model_path} epochs={epochs}")
    from ultralytics import YOLO
    model = YOLO(model_path)
    results = model.train(data=str(aug_yaml), epochs=epochs, imgsz=640, batch=2, device='cpu', verbose=True)
    progress_callback(f"[E2E] YOLO学習完了: {results}")
    return {
        "dataset_yaml": str(dataset_yaml),
        "augmented_yaml": str(aug_yaml),
        "train_results": results
    } 