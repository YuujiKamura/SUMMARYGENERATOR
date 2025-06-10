import os
import tempfile
from pathlib import Path
from src.yolo_dataset_exporter import YoloDatasetExporter
from src.utils.path_manager import PathManager
from src.utils.bbox_convert import xyxy_abs_to_xywh_norm

def test_yolo_exporter_with_master_json():
    pm = PathManager()
    master_json = str(pm.project_root / "data" / "image_preview_cache_master.json")
    assert os.path.exists(master_json), f"マスタJSONが存在しません: {master_json}"
    # 一時ディレクトリに出力
    with tempfile.TemporaryDirectory() as tmpdir:
        exporter = YoloDatasetExporter([master_json], output_dir=tmpdir, val_ratio=0.0)
        # エクスポート実行
        result = exporter.export(force_flush=True)
        label_dir_train = Path(result["output_dir"]) / "labels" / "train"
        label_files = list(label_dir_train.glob("*.txt"))
        assert label_files, "ラベルファイルが出力されていない"
        # ラベルファイル内容検証
        for lf in label_files:
            with open(lf, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split()
                    assert len(parts) == 5, f"ラベル行の要素数不正: {line}"
                    # クラスID, x, y, w, hが全て数値であること
                    try:
                        [float(p) for p in parts]
                    except Exception:
                        assert False, f"ラベル行に数値以外が含まれる: {line}"
        # クラス名リストが空でないこと
        assert len(exporter.classes) > 0
        # 画像リストが空でないこと
        assert len(exporter.images) > 0
        # 各画像のアノテーションが正しく構築されていること
        for anns in exporter.annotations.values():
            for ann in anns:
                assert "class_id" in ann
                assert "box" in ann
                assert isinstance(ann["box"], list)
                assert len(ann["box"]) == 4
        # bbox正規化の動作確認
        for anns in exporter.annotations.values():
            for ann in anns:
                box = ann["box"]
                # 仮の画像サイズ
                img_w, img_h = 1280, 960
                x, y, w, h = xyxy_abs_to_xywh_norm(*box, img_w, img_h)
                assert 0.0 <= x <= 1.0
                assert 0.0 <= y <= 1.0
                assert 0.0 < w <= 1.0
                assert 0.0 < h <= 1.0 