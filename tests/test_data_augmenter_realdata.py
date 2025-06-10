import pytest
from pathlib import Path
import yaml
import time
from datetime import datetime
from src.utils.data_augmenter import augment_dataset
from src.utils.yolo_threads import YoloTrainThread
from PyQt6.QtCore import QEventLoop, QTimer
import tempfile, shutil, os, glob, json
from src.yolo_dataset_exporter import YoloDatasetExporter
from src.utils.path_manager import path_manager

def test_realdata_augmentation_and_train(qtbot, capfd):
    print("=== データ拡張テスト開始 ===", flush=True)
    # dataset.yamlのパス
    dataset_yaml = Path(r"C:/Users/yuuji/Sanyuu2Kouku/cursor_tools/PhotoCategorizer/runs/train/test_roles/yolo_export_20250520_140248/dataset.yaml")
    print(f"[TEST] dataset_yaml: {dataset_yaml}", flush=True)
    with open(dataset_yaml, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    # 画像・ラベルディレクトリの解決
    base = Path(config['path'])
    img_dir = base / config['train']
    label_dir = base / 'labels/train'
    # ユニークな拡張データセット出力先
    out_dir = Path.cwd() / datetime.now().strftime('augmented_pytest_%Y%m%d_%H%M%S')
    print(f'[TEST] 拡張処理開始: {img_dir=} {label_dir=} {out_dir=}', flush=True)
    def progress(msg):
        print(f'[AUG] {msg}', flush=True)
    # 拡張実行（n_augment=3）
    result = augment_dataset(
        src_img_dir=str(img_dir),
        src_label_dir=str(label_dir),
        dst_dir=str(out_dir),
        n_augment=3,
        progress_callback=progress
    )
    print(f'[TEST] 拡張後データセットパス: {out_dir}', flush=True)
    # 検証: 拡張画像・ラベル・dataset.yamlが生成されていること
    assert result['original_images'] > 0
    assert result['augmented_images'] > 0
    assert (out_dir / 'images').exists()
    assert (out_dir / 'labels').exists()
    assert (out_dir / 'dataset.yaml').exists()
    print("=== データ拡張テスト終了 ===", flush=True)

    # YOLO学習（YoloTrainThreadを使う）
    # 学習用のモデル（yolov8n.ptなど）を自動選択
    model_path = None
    for candidate in [Path('yolov8n.pt'), Path('yolo/yolov8n.pt'), Path('models/yolov8n.pt')]:
        if candidate.exists():
            model_path = str(candidate)
            break
    assert model_path, 'yolov8n.ptが見つかりません'

    # 学習スレッドのセットアップ
    dataset_yaml_path = str(out_dir / 'dataset.yaml')
    epochs = 1  # テストなので1エポック
    exp_name = 'pytest_aug_train'
    thread = YoloTrainThread(model_path, dataset_yaml_path, epochs, exp_name)
    results = {}
    def on_output(msg):
        print(f'[TRAIN] {msg}')
    def on_finished(code, result):
        results['code'] = code
        results['result'] = result
    thread.output_received.connect(on_output)
    thread.process_finished.connect(on_finished)
    thread.start()

    # イベントループで完了待ち（最大10分）
    loop = QEventLoop()
    def check():
        if 'code' in results:
            loop.quit()
        # 途中経過を都度表示
        out, err = capfd.readouterr()
        if out:
            print(out, end='')
    timer = QTimer()
    timer.timeout.connect(check)
    timer.start(1000)
    qtbot.waitSignal(thread.process_finished, timeout=600000)
    loop.exec()
    timer.stop()

    # 学習が正常終了したことを検証
    assert results['code'] == 0
    assert 'exp_name' in results['result']
    print(f'学習に使ったデータセット: {dataset_yaml_path}')

def test_individual_json_to_yolo_and_augment(qtbot, capfd):
    """
    image_preview_cache内の個別JSONをYOLOデータセットに変換し、さらに5倍拡張し、拡張後のサマリーを検証する。
    複数JSONを順に試し、image_pathが実在するものだけでテストする。
    """
    cache_dir = os.path.join(os.path.dirname(__file__), "..", "src", "image_preview_cache")
    json_files = glob.glob(os.path.join(cache_dir, "*.json"))
    assert json_files, "image_preview_cacheに個別JSONがありません"
    # role_mappingから有効クラス名リストを取得
    with open(path_manager.role_mapping, encoding="utf-8") as f:
        role_mapping = json.load(f)
    valid_roles = set()
    for v in role_mapping.values():
        valid_roles.update(v.get("roles", []))
    tested = 0
    for json_path in json_files:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        img_path = data.get("image_path")
        bboxes = data.get("bboxes", [])
        # 有効なラベルが1つ以上あるか判定
        has_valid = False
        for bbox in bboxes:
            role = bbox.get("role")
            label = bbox.get("label")
            class_name = role if role else label
            if class_name in valid_roles:
                has_valid = True
                break
        if not (img_path and os.path.exists(img_path) and has_valid):
            continue
        # 2. YOLOデータセット変換
        temp_dir = tempfile.mkdtemp(prefix="yolo_oneimg_test_")
        exporter = YoloDatasetExporter([json_path], output_dir=temp_dir, val_ratio=0.0)
        result = exporter.export(mode='all', force_flush=True)
        # 3. 拡張処理
        src_img_dir = os.path.join(temp_dir, "images", "train")
        src_label_dir = os.path.join(temp_dir, "labels", "train")
        aug_dir = os.path.join(temp_dir, "augmented")
        aug_result = augment_dataset(
            src_img_dir=src_img_dir,
            src_label_dir=src_label_dir,
            dst_dir=aug_dir,
            n_augment=5
        )
        # 4. サマリー検証
        assert os.path.exists(aug_dir)
        assert os.path.exists(os.path.join(aug_dir, "images"))
        assert os.path.exists(os.path.join(aug_dir, "labels"))
        assert os.path.exists(os.path.join(aug_dir, "dataset.yaml"))
        assert aug_result["original_images"] > 0
        print(f"[TEST] 個別JSON→YOLO変換＋拡張サマリー: {aug_result}")
        shutil.rmtree(temp_dir)
        tested += 1
        if tested >= 2:
            break
    if tested == 0:
        pytest.skip("有効なラベルを持つ個別JSONが見つかりませんでした")

def test_specific_json_to_yolo_and_augment(qtbot, capfd):
    """
    特定の個別JSON（10b809b47d280ac15e51ead474035d7507c3ce30.json）で変換＋拡張テスト
    """
    json_path = os.path.join(os.path.dirname(__file__), "..", "src", "image_preview_cache", "10b809b47d280ac15e51ead474035d7507c3ce30.json")
    assert os.path.exists(json_path), f"JSONが存在しません: {json_path}"
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    img_path = data.get("image_path")
    assert img_path and os.path.exists(img_path), f"画像が存在しません: {img_path}"
    # 2. YOLOデータセット変換
    temp_dir = tempfile.mkdtemp(prefix="yolo_oneimg_test_")
    try:
        exporter = YoloDatasetExporter([json_path], output_dir=temp_dir, val_ratio=0.0)
        result = exporter.export(mode='all', force_flush=True)
        # 3. 拡張処理
        src_img_dir = os.path.join(temp_dir, "images", "train")
        src_label_dir = os.path.join(temp_dir, "labels", "train")
        aug_dir = os.path.join(temp_dir, "augmented")
        aug_result = augment_dataset(
            src_img_dir=src_img_dir,
            src_label_dir=src_label_dir,
            dst_dir=aug_dir,
            n_augment=5
        )
        # 4. サマリー検証
        assert os.path.exists(aug_dir)
        assert os.path.exists(os.path.join(aug_dir, "images"))
        assert os.path.exists(os.path.join(aug_dir, "labels"))
        assert os.path.exists(os.path.join(aug_dir, "dataset.yaml"))
        assert aug_result["original_images"] > 0
        print(f"[TEST] 指定JSON→YOLO変換＋拡張サマリー: {aug_result}")
    except Exception as e:
        import traceback
        print(f"[ERROR] 変換＋拡張失敗: {e}\n{traceback.format_exc()}")
        raise
    finally:
        shutil.rmtree(temp_dir) 