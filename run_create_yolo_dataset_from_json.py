import sys
import argparse
from src.data.json_to_db import create_table, insert_from_json
from src.data.db_to_yolo_dataset import main as yolo_dataset_main
from src.data.augment_yolo_dataset import main as augment_main
from src.data.validate_db_bboxes import validate_bboxes_in_db
from pathlib import Path
import sqlite3
from glob import glob
import datetime

def train_yolov8(yaml_path, epochs, project_dir):
    try:
        from ultralytics import YOLO
    except ImportError:
        print('ultralyticsパッケージがインストールされていません。pip install ultralytics でインストールしてください。')
        return
    model = YOLO('yolov8n.pt')  # 軽量モデルで初期化（必要に応じて変更可）
    import sys
    from pathlib import Path
    logs_dir = Path(__file__).parent / 'logs'
    logs_dir.mkdir(exist_ok=True)
    train_log_path = logs_dir / '04_yolov8_train.log'
    import contextlib
    with open(train_log_path, 'w', encoding='utf-8') as logf:  # ← 'w'で明示
        with contextlib.redirect_stdout(logf), contextlib.redirect_stderr(logf):
            model.train(data=str(yaml_path), epochs=epochs, project=str(project_dir), name='exp', exist_ok=True)
    print(f"[INFO] 学習ログを出力しました: {train_log_path}")

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
    parser.add_argument('--epochs', type=int, default=5, help='YOLO学習のエポック数')
    args = parser.parse_args()

    print(f'日付範囲: {args.date_from} ～ {args.date_to}')
    print(f'オーグメント拡張数: {args.augment_num}')
    print(f'エポック数: {args.epochs}')

    print('DB登録を開始します')
    db_path = Path(__file__).parent / 'src' / 'data' / 'model_training_cache.db'
    print(f'[INFO] DB登録で参照するDBファイル: {db_path.resolve()}')
    create_table()
    insert_from_json()
    print('DB登録が完了しました')
    # DB内容をダンプ
    try:
        import sqlite3, json
        db_path = Path(__file__).parent / 'src' / 'data' / 'model_training_cache.db'
        print(f'[INFO] DBダンプで参照するDBファイル: {db_path.resolve()}')
        logs_dir = Path(__file__).parent / 'logs'
        logs_dir.mkdir(exist_ok=True)
        out_path = logs_dir / '01_db_dump.json'
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('SELECT filename, image_path, bboxes FROM image_cache')
        rows = c.fetchall()
        conn.close()
        result = []
        for filename, image_path, bboxes in rows:
            try:
                bboxes_json = json.loads(bboxes)
            except Exception:
                bboxes_json = bboxes
            result.append({
                'filename': filename,
                'image_path': image_path,
                'bboxes': bboxes_json
            })
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"[INFO] DB内容をダンプしました: {out_path} (件数: {len(result)})")
    except Exception as e:
        print(f"[警告] DBダンプ失敗: {e}")
    print('YOLO DataSet生成を開始します')
    print(f'[INFO] YOLOデータセット生成で参照するDBファイル: {db_path.resolve()}')
    # 日付＋時刻でディレクトリ名を生成
    now = datetime.datetime.now()
    date_str = now.strftime('%Y%m%d_%H%M%S')
    datasets_base = Path(__file__).parent / 'src' / 'datasets'
    dataset_dir_name = f'yolo_dataset_all_{date_str}'
    dataset_dir = datasets_base / dataset_dir_name
    # YOLOデータセット生成（mainに出力先パスを渡せる場合は渡す。渡せない場合はmain内で修正が必要）
    yolo_dataset_main(dataset_dir)
    logs_dir = Path(__file__).parent / 'logs'
    yolo_dump_path = logs_dir / '02_yolo_dataset_dump.json'
    # ここでの移動/コピー処理は不要になったため削除
    print(f"[INFO] YOLO DataSet生成ダンプ: {yolo_dump_path}")
    print('YOLO DataSet生成が完了しました')
    print('オーグメント拡張画像生成を開始します')
    augment_main(dataset_dir, args.augment_num)
    aug_log_path = Path(__file__).parent / 'src' / 'data' / 'augment_invalid_bboxes.log'
    logs_dir = Path(__file__).parent / 'logs'
    aug_log_out = logs_dir / '03_augment_invalid_bboxes.log'
    if Path(aug_log_path).exists():
        import shutil
        shutil.copy2(aug_log_path, aug_log_out)
        print(f"[INFO] オーグメント異常bboxログ: {aug_log_out}")
    else:
        print(f"[INFO] オーグメント異常bboxログが見つかりません: {aug_log_path}")
    print('オーグメント拡張画像生成が完了しました')
    # YOLOv8学習（Python APIで実行）
    print('YOLOv8学習を開始します')
    yaml_path = dataset_dir / 'dataset.yaml'
    project_dir = dataset_dir / 'train_run'
    db_path = Path(__file__).parent / 'src' / 'data' / 'model_training_cache.db'
    validate_bboxes_in_db(db_path)
    train_yolov8(yaml_path, args.epochs, project_dir)
    logs_dir = Path(__file__).parent / 'logs'
    train_log_path = logs_dir / '04_yolov8_train.log'
    # ultralyticsの学習ログは標準でファイル出力されないため、必要ならここでキャプチャして保存も可
    print(f"[INFO] YOLOv8学習結果: {project_dir}")
    print(f"[INFO] 学習ログ(仮): {train_log_path}")
    print('YOLOv8学習が完了しました')
    # delete_aug_records_from_db()  # ← 不要なので削除
    # 一連の処理の最後でDBファイルを削除
    import os
    if db_path.exists():
        os.remove(db_path)
        print(f'[INFO] モデルトレーニング用DBファイルを削除しました: {db_path.resolve()}')

if __name__ == '__main__':
    main()