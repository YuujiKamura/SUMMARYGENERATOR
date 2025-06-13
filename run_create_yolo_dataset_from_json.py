import sys
import argparse
from pathlib import Path
import datetime
import shutil

def train_yolo_model(yaml_path, epochs, project_dir, model_path=None):
    try:
        from ultralytics import YOLO
    except ImportError:
        print('ultralyticsパッケージがインストールされていません。pip install ultralytics でインストールしてください。')
        return
    from pathlib import Path
    if model_path is None:
        model_path = Path(__file__).parent / 'src' / 'yolo' / 'yolo11n.pt'
    else:
        model_path = Path(model_path)
    model = YOLO(str(model_path))
    logs_dir = Path(__file__).parent / 'logs'
    logs_dir.mkdir(exist_ok=True)
    # ログファイル名をモデル名で動的に
    log_suffix = model_path.stem.replace('.', '_')
    train_log_path = logs_dir / f'04_train_{log_suffix}.log'
    import contextlib
    model_name = model_path.name
    with open(train_log_path, 'w', encoding='utf-8') as logf:
        with contextlib.redirect_stdout(logf), contextlib.redirect_stderr(logf):
            model.train(data=str(yaml_path), epochs=epochs, project=str(project_dir), name='exp', exist_ok=True)
    print(f"[INFO] 学習ログを出力しました: {train_log_path} (ベースモデル: {model_name})")

def find_latest_yolo_dataset_dir(base_dir):
    import re
    from pathlib import Path
    candidates = list(Path(base_dir).glob('yolo_dataset_all_*'))
    if not candidates:
        raise FileNotFoundError('yolo_dataset_all_* ディレクトリが見つかりません')
    # タイムスタンプ部分で降順ソート
    def extract_ts(p):
        m = re.search(r'yolo_dataset_all_\d+_(\d+)', p.name)
        return int(m.group(1)) if m else 0
    candidates.sort(key=extract_ts, reverse=True)
    return candidates[0]

def main():
    parser = argparse.ArgumentParser(description='YOLO DataSetワンストップ生成・学習スクリプト')
    parser.add_argument('--date-from', type=str, default=None, help='対象画像の日付範囲（開始）例: 20250601')
    parser.add_argument('--date-to', type=str, default=None, help='対象画像の日付範囲（終了）例: 20250610')
    parser.add_argument('--augment-num', type=int, default=5, help='各画像ごとのオーグメント拡張数')
    parser.add_argument('--epochs', type=int, default=100, help='YOLO学習のエポック数')
    args = parser.parse_args()

    print(f'日付範囲: {args.date_from} ～ {args.date_to}')
    print(f'オーグメント拡張数: {args.augment_num}')
    print(f'エポック数: {args.epochs}')

    # --- 既存のworkdirを強制削除してクリーンに ---
    workdir = Path(__file__).parent / 'workdir'
    if workdir.exists():
        print(f'[INFO] 既存のworkdirを削除します: {workdir.resolve()}')
        shutil.rmtree(workdir, ignore_errors=True)

    # 1. DB→YOLO形式ファイル出力
    print('DB登録・YOLOデータセット一時出力を開始します')
    from src.data.json_to_db import create_table, insert_from_json
    from src.data.db_to_yolo_dataset import YoloDatasetBuilder
    db_path = Path(__file__).parent / 'src' / 'data' / 'model_training_cache.db'
    workdir = Path(__file__).parent / 'workdir'
    yolo_tmp_dir = workdir / 'yolo_raw'
    yolo_tmp_dir.mkdir(parents=True, exist_ok=True)
    create_table()
    insert_from_json()
    builder = YoloDatasetBuilder(out_dir=yolo_tmp_dir)
    builder.process()
    print(f'[INFO] DB→YOLOファイル出力完了: {yolo_tmp_dir}')

    # 2. オーグメント
    print('オーグメント拡張画像生成を開始します')
    from src.data.augment_yolo_dataset import augment_dataset
    augment_dataset(yolo_tmp_dir, augment_num=args.augment_num)
    print(f'[INFO] オーグメント拡張完了: {yolo_tmp_dir}')

    # 3. train/val分割
    print('train/val分割を開始します')
    from src.yolo_dataset_exporter import YoloDatasetExporter
    now = datetime.datetime.now()
    date_str = now.strftime('%Y%m%d_%H%M%S')
    datasets_base = Path(__file__).parent / 'src' / 'datasets'
    dataset_dir_name = f'yolo_dataset_all_{date_str}'
    dataset_dir = datasets_base / dataset_dir_name
    # YoloDatasetExporterは画像リストJSONを受け取る設計なので、ここでは一時的に画像リストを作成する必要がある場合は対応
    # ここではbuilder.image_bboxesを使って画像リストを作成する例
    image_list_json = workdir / 'image_list.json'
    import json
    with open(image_list_json, 'w', encoding='utf-8') as f:
        json.dump(builder.image_bboxes, f, ensure_ascii=False, indent=2)
    exporter = YoloDatasetExporter([str(image_list_json)], output_dir=str(dataset_dir), val_ratio=0.2)
    exporter.export(force_flush=True)
    print(f'[INFO] train/val分割・最終データセット出力完了: {dataset_dir}')

    # 4. YOLO学習
    print('YOLO学習を開始します')
    from src.data.validate_db_bboxes import validate_bboxes_in_db
    validate_bboxes_in_db(db_path)
    yaml_path = dataset_dir / 'dataset.yaml'
    project_dir = dataset_dir / 'train_run'
    model_path = Path(__file__).parent / 'src' / 'yolo' / 'yolo11n.pt'
    train_yolo_model(yaml_path, args.epochs, project_dir, model_path)
    print(f'[INFO] 学習結果: {project_dir}')
    print(f'[INFO] 学習ログ: logs/04_train_{model_path.stem.replace(".", "_")}.log')
    print('YOLO学習が完了しました')

    # 5. 一時ファイル削除
    if db_path.exists():
        db_path.unlink()
        print(f'[INFO] モデルトレーニング用DBファイルを削除しました: {db_path.resolve()}')
    # yolo_data.db も削除
    yolo_db_path = Path(__file__).parent / 'src' / 'yolo_data.db'
    if yolo_db_path.exists():
        yolo_db_path.unlink()
        print(f'[INFO] YOLO用DBファイルを削除しました: {yolo_db_path.resolve()}')
    shutil.rmtree(workdir, ignore_errors=True)
    print(f'[INFO] 一時ワークディレクトリを削除しました: {workdir.resolve()}')

if __name__ == '__main__':
    main()