import sys
import argparse
import subprocess
from src.data.json_to_db import create_table, insert_from_json
from src.data.db_to_yolo_dataset import main as yolo_dataset_main
from src.data.augment_yolo_dataset import main as augment_main
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description='YOLO DataSetワンストップ生成・学習スクリプト')
    parser.add_argument('--date-from', type=str, default=None, help='対象画像の日付範囲（開始）例: 20250601')
    parser.add_argument('--date-to', type=str, default=None, help='対象画像の日付範囲（終了）例: 20250610')
    parser.add_argument('--augment-num', type=int, default=2, help='各画像ごとの水増し（Augmentation）数')
    parser.add_argument('--epochs', type=int, default=100, help='YOLO学習のエポック数')
    args = parser.parse_args()

    print(f'日付範囲: {args.date_from} ～ {args.date_to}')
    print(f'拡張数: {args.augment_num}')
    print(f'エポック数: {args.epochs}')

    print('DB登録を開始します')
    create_table()
    insert_from_json()
    print('DB登録が完了しました')
    print('YOLO DataSet生成を開始します')
    yolo_dataset_main()
    print('YOLO DataSet生成が完了しました')
    print('水増し画像生成を開始します')
    augment_main()
    print('水増し画像生成が完了しました')

    # YOLOv8学習自動実行
    print('YOLOv8学習を開始します')
    dataset_dir = Path(__file__).parent / 'src' / 'datasets' / 'yolo_dataset_all_3_20250610_142237'
    yaml_path = dataset_dir / 'dataset.yaml'
    weights_path = dataset_dir / 'train_run' / 'weights' / 'best.pt'
    # ultralytics/yolo コマンドで学習
    cmd = [
        sys.executable, '-m', 'ultralytics', 'train',
        '--data', str(yaml_path),
        '--epochs', str(args.epochs),
        '--project', str(dataset_dir / 'train_run'),
        '--name', 'exp',
        '--exist-ok'
    ]
    print(' '.join(map(str, cmd)))
    subprocess.run(cmd, check=True)
    print('YOLOv8学習が完了しました')

if __name__ == '__main__':
    main() 