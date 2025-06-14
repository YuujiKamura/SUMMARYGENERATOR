from pathlib import Path
from src.io.image_io import safe_imread_with_temp
from src.bbox.types import BBoxYOLO

def folder_source(dataset_dir):
    images_dir = Path(dataset_dir) / 'images' / 'train'
    labels_dir = Path(dataset_dir) / 'labels' / 'train'
    for img_path in images_dir.glob('*.jpg'):
        if img_path.name.startswith('aug'):
            continue
        label_path = labels_dir / (img_path.stem + '.txt')
        if not label_path.exists():
            continue
        image = safe_imread_with_temp(img_path)
        if image is None:
            continue
        h, w = image.shape[:2]
        bboxes = []
        with open(label_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) != 5:
                    continue
                cid, x, y, bw, bh = map(float, parts)
                bboxes.append(BBoxYOLO(int(cid), x, y, bw, bh))
        if not bboxes:
            continue
        yield img_path, image, bboxes
