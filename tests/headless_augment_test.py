import sys
from pathlib import Path
import yaml
from src.utils.data_augmenter import augment_dataset

def main():
    # dataset.yamlのパス
    dataset_yaml = Path(r"C:/Users/yuuji/Sanyuu2Kouku/cursor_tools/PhotoCategorizer/runs/train/test_roles/yolo_export_20250520_140248/dataset.yaml")
    with open(dataset_yaml, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    # 画像・ラベルディレクトリの解決
    base = Path(config['path'])
    img_dir = base / config['train']
    label_dir = base / 'labels/train'
    out_dir = base / 'augmented_headless_test'
    # 拡張実行
    result = augment_dataset(
        src_img_dir=str(img_dir),
        src_label_dir=str(label_dir),
        dst_dir=str(out_dir),
        n_augment=2,
        progress_callback=print
    )
    print('拡張結果:', result)

if __name__ == '__main__':
    main() 