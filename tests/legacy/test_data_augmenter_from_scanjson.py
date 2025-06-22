import tempfile
import shutil
from pathlib import Path
from src.yolo_dataset_exporter import YoloDatasetExporter
from src.utils.data_augmenter import augment_dataset
import yaml
import pytest

def test_augment_from_scanjson(tmp_path):
    # 1. scan_for_images_dataset.jsonからYOLOデータセットを一時出力
    scan_json = Path(__file__).parent.parent.parent / "src" / "scan_for_images_dataset.json"
    yolo_out_dir = tmp_path / "yolo_dataset"
    exporter = YoloDatasetExporter([str(scan_json)], output_dir=str(yolo_out_dir), val_ratio=0.1)
    export_result = exporter.export(force_flush=True)
    dataset_yaml = yolo_out_dir / "dataset.yaml"
    assert dataset_yaml.exists()
    # 2. augment_datasetで拡張
    with open(dataset_yaml, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    base = Path(config['path'])
    img_dir = base / config['train']
    label_dir = base / 'labels/train'
    aug_out_dir = tmp_path / "augmented_dataset"
    result = augment_dataset(
        src_img_dir=str(img_dir),
        src_label_dir=str(label_dir),
        dst_dir=str(aug_out_dir),
        n_augment=2
    )
    # 3. 拡張後のimages/labels/dataset.yamlの存在・内容を検証
    assert (aug_out_dir / 'images').exists()
    assert (aug_out_dir / 'labels').exists()
    assert (aug_out_dir / 'dataset.yaml').exists()
    # 画像・ラベルファイル数が元より増えていること
    orig_imgs = list((img_dir).glob("*.jpg"))
    aug_imgs = list((aug_out_dir / 'images').glob("*.jpg"))
    assert len(aug_imgs) > len(orig_imgs)
    # dataset.yamlのnamesが空でないこと
    with open(aug_out_dir / 'dataset.yaml', 'r', encoding='utf-8') as f:
        ydata = yaml.safe_load(f)
    assert 'names' in ydata and ydata['names']

    # 4. 拡張後データセットでYOLO学習が最後まで走るか検証
    try:
        from ultralytics import YOLO
        model_path = Path(__file__).parent.parent.parent / "yolo" / "yolov8n.pt"
        if not model_path.exists():
            pytest.skip("yolov8n.ptが見つかりません")
        model = YOLO(str(model_path))
        print(f"[TEST] YOLO学習開始: data={aug_out_dir / 'dataset.yaml'} model={model_path}")
        results = model.train(data=str(aug_out_dir / 'dataset.yaml'), epochs=5, imgsz=640, batch=2, device='cpu', verbose=True)
        print(f"[TEST] YOLO学習結果: {results}")
        assert results is not None
    except Exception as e:
        print(f"[TEST][ERROR] YOLO学習例外: {e}")
        pytest.fail(f"YOLO学習が最後まで走りませんでした: {e}") 