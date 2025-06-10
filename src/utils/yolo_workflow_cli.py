import argparse
import subprocess
from pathlib import Path
import sys

def main():
    parser = argparse.ArgumentParser(description="YOLOワンストップワークフローCLI")
    parser.add_argument('--json', type=str, required=True, help='image_preview_cache_master.jsonのパス')
    parser.add_argument('--role', type=str, default=None, help='抽出するrole名（カンマ区切り可）')
    parser.add_argument('--desc', type=str, default='', help='データセット説明')
    parser.add_argument('--model', type=str, default=None, help='YOLOモデルパス（省略時はsrc/yolo/yolov8n.pt）')
    parser.add_argument('--val_ratio', type=float, default=0.2, help='val比率')
    args = parser.parse_args()

    # 1. JSON→DB登録
    print("[STEP1] JSON→DB登録...")
    db_init_cmd = [
        sys.executable, '-m', 'src.utils.init_yolo_db'
    ]
    print(f"[INFO] DB初期化コマンド: {' '.join(db_init_cmd)}")
    try:
        subprocess.run(db_init_cmd, check=True)
    except Exception as e:
        print(f"[ERROR] DB初期化失敗: {e}")
        sys.exit(1)

    # 2. DataSet変換・拡張・YOLO学習
    print("[STEP2] DataSet変換・拡張・YOLO学習...")
    dataset_cli_cmd = [
        sys.executable, '-m', 'src.utils.create_yolo_dataset_cli',
        '--json', args.json,
        '--val_ratio', str(args.val_ratio)
    ]
    if args.role:
        dataset_cli_cmd += ['--role', args.role]
    if args.desc:
        dataset_cli_cmd += ['--desc', args.desc]
    if args.model:
        dataset_cli_cmd += ['--model', args.model]
    print(f"[INFO] DataSet/YOLOコマンド: {' '.join(dataset_cli_cmd)}")
    try:
        subprocess.run(dataset_cli_cmd, check=True)
    except Exception as e:
        print(f"[ERROR] DataSet/YOLO処理失敗: {e}")
        sys.exit(1)

    print("[OK] ワンストップYOLOワークフロー完了")

if __name__ == "__main__":
    main() 