import os
import pytest
from pathlib import Path
from src.utils.yolo_threads import YoloTrainThread
from src.widgets.data_augment_widget import DataAugmentWidget
from PyQt6.QtCore import QThread
from src.utils.path_manager import path_manager

@pytest.mark.qt
@pytest.mark.slow
def test_data_augment_and_yolo_train_real(qtbot, tmp_path):
    # --- データ拡張 ---
    src_img_dir = path_manager.project_root / "managed_files" / "current" / "yolo_dataset" / "images" / "train"
    src_label_dir = path_manager.project_root / "managed_files" / "current" / "yolo_dataset" / "labels" / "train"
    assert src_img_dir.exists(), "拡張元画像ディレクトリが存在しません"
    assert src_label_dir.exists(), "拡張元ラベルディレクトリが存在しません"
    dst_dir = tmp_path / "augmented_dataset"
    dst_dir.mkdir(parents=True, exist_ok=True)

    # DataAugmentWidgetを使って5枚だけ拡張
    widget = DataAugmentWidget()
    widget.src_img_edit.setText(str(src_img_dir))
    widget.src_label_edit.setText(str(src_label_dir))
    widget.dst_dir_edit.setText(str(dst_dir))
    widget.count_spin.setValue(5)
    widget.show()  # UI不要なら省略可
    qtbot.addWidget(widget)

    def do_augment(src_img, src_label, dst, n_aug):
        (Path(dst) / "images").mkdir(parents=True, exist_ok=True)
        (Path(dst) / "labels").mkdir(parents=True, exist_ok=True)
        imgs = list(Path(src_img).glob("*.jpg"))[:n_aug]
        labels = list(Path(src_label).glob("*.txt"))[:n_aug]
        for img in imgs:
            to = Path(dst) / "images" / img.name
            to.write_bytes(img.read_bytes())
        for lbl in labels:
            to = Path(dst) / "labels" / lbl.name
            to.write_text(lbl.read_text(encoding="utf-8"), encoding="utf-8")
        widget.augmentation_finished.emit(0, {"msg": "拡張完了"})

    widget.augmentation_started.connect(do_augment)
    widget.start_data_augmentation()
    qtbot.waitSignal(widget.augmentation_finished, timeout=60000)

    # 拡張後の画像・ラベルが生成されているか
    aug_img_dir = dst_dir / "images"
    aug_label_dir = dst_dir / "labels"
    assert aug_img_dir.exists() and aug_label_dir.exists(), "拡張後の画像/ラベルディレクトリが無い"
    aug_imgs = list(aug_img_dir.glob("*.jpg")) + list(aug_img_dir.glob("*.JPG"))
    aug_labels = list(aug_label_dir.glob("*.txt")) + list(aug_label_dir.glob("*.TXT"))
    assert len(aug_imgs) >= 5, f"拡張画像が5枚未満: {len(aug_imgs)}"
    assert len(aug_labels) >= 5, f"拡張ラベルが5枚未満: {len(aug_labels)}"

    # --- YOLO学習 ---
    # dataset.yamlを生成（簡易）
    dataset_yaml = dst_dir / "dataset.yaml"
    with open(dataset_yaml, "w", encoding="utf-8") as f:
        f.write(f"""
path: {dst_dir}
train: images
val: images
names: ['class0']
""")
    model_path = str(path_manager.yolov8n)
    exp_name = "pytest_yolo_train"
    project = str(tmp_path / "runs")
    epochs = 5

    thread = YoloTrainThread(
        model_path=model_path,
        dataset_yaml=str(dataset_yaml),
        epochs=epochs,
        exp_name=exp_name,
        project=project
    )
    outputs = []
    result = {}
    def on_output(msg): outputs.append(msg)
    def on_finish(code, res): result['code'] = code; result['res'] = res
    thread.output_received.connect(on_output)
    thread.process_finished.connect(on_finish)
    thread.run()  # 直接呼ぶ
    print("YOLO学習出力:", outputs)
    print("YOLO学習結果:", result)
    assert 'code' in result, f"process_finishedが呼ばれていません: {outputs}"
    assert result['code'] == 0, f"学習が失敗: {result}"
    assert "best_model" in result['res']
    assert os.path.exists(result['res']["best_model"]), "best.ptが生成されていません"
    assert "results" in result['res']
    assert "metrics" in result['res']["results"]
    assert any("トレーニングが完了しました" in o for o in outputs) 