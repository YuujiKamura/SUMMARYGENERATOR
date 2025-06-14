import os
from pathlib import Path
from src.utils.yolo_dataset_exporter import YoloDatasetExporter
from src.utils.path_manager import path_manager
import subprocess

def test_yolo_exporter_with_db():
    # DB依存のテストに修正
    import tempfile
    db_path = path_manager.yolo_db
    # 既存DBを削除してから初期化
    if os.path.exists(db_path):
        os.remove(db_path)
    # DB初期化スクリプトを実行
    init_script = path_manager.project_root / "scripts" / "run_init_yolo_db.py"
    assert os.path.exists(init_script), f"DB初期化スクリプトが存在しません: {init_script}"
    subprocess.run(["python", str(init_script)], check=True)
    assert os.path.exists(db_path), f"DBファイルが存在しません: {db_path}"
    with tempfile.TemporaryDirectory() as tmpdir:
        exporter = YoloDatasetExporter(output_dir=tmpdir, val_ratio=0.0)
        result = exporter.export(force_flush=True)
        label_dir_train = Path(result["output_dir"]) / "labels" / "train"
        label_files = list(label_dir_train.glob("*.txt"))
        assert label_files, "ラベルファイルが出力されていない"
        for lf in label_files:
            with open(lf, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split()
                    assert len(parts) == 5, f"ラベル行の要素数不正: {line}"
                    try:
                        [float(p) for p in parts]
                    except Exception:
                        assert False, f"ラベル行に数値以外が含まれる: {line}"
        assert len(exporter.classes) > 0
        assert len(exporter.images) > 0
        for v in exporter.annotations.values():
            for ann in v.get('anns', []):
                assert "class_id" in ann
                assert "box" in ann
                assert isinstance(ann["box"], list)
                assert len(ann["box"]) == 4