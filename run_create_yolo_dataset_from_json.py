import sys
# --- OpenCV警告・stderr抑制 ---
def _suppress_cv2_warnings() -> None:
    try:
        import cv2, contextlib, io
        if hasattr(cv2, "setLogLevel"):
            with contextlib.redirect_stderr(io.StringIO()):
                cv2.setLogLevel(3)  # 3 = ERROR
    except ImportError:
        pass  # OpenCV 未導入なら無視

_suppress_cv2_warnings()

import argparse
from pathlib import Path
import datetime
import json
import logging
from typing import List, Dict, Any

# --- logging設定 ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# --- 乱数シード固定（再現性担保） ---
def set_seed(seed: int = 42):
    import random
    import numpy as np
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
    except ImportError:
        pass

set_seed()

class AugmentationManager:
    """
    オーグメント拡張のための「作業用YOLOデータセットディレクトリの生成」と「拡張処理のみ」を担当する
    """
    def __init__(self, log, model_trainer):
        self.log = log
        self.model_trainer = model_trainer

    def prepare_workdir_from_db(self, db_path, work_dir, val_ratio=0.2):
        # DBからYOLOデータセット用の作業ディレクトリを生成
        self.model_trainer.export_labels(work_dir, db_path, val_ratio=val_ratio, force_flush=True)
        self.log.info(f'[AUG] 拡張用作業ディレクトリ生成: {work_dir}')
        return work_dir

    def run_augmentation(self, input_dir, augment_num, output_dir, db_path):
        # input_dir: 拡張用のYOLOデータセットディレクトリ
        from src.augment.runner import main as augment_main
        summary = augment_main(input_dir, n=augment_num, output_dir=output_dir, show_progress=True, return_summary=True, db_path=db_path)
        self.log.info(f'[AUG] オーグメント拡張完了: {output_dir}')
        self.log.info(f'[AUG] augmentサマリー: {summary}')
        return summary

class ModelTrainer:
    """
    YOLO学習の実行・ログ管理の責務のみを持つ（データセット出力はYoloDatasetExporterに委譲）
    """
    def __init__(self, log):
        self.log = log

    def train(self, yaml_path, epochs, project_dir, model_path=None):
        try:
            from ultralytics import YOLO
        except ImportError:
            self.log.error('ultralyticsパッケージがインストールされていません。pip install ultralytics でインストールしてください。')
            return
        from pathlib import Path
        if model_path is None:
            model_path = Path(__file__).parent / 'src' / 'yolo' / 'yolo11n.pt'
        else:
            model_path = Path(model_path)
        model = YOLO(str(model_path))
        logs_dir = Path(__file__).parent / 'logs'
        logs_dir.mkdir(exist_ok=True)
        log_suffix = model_path.stem.replace('.', '_')
        train_log_path = logs_dir / f'04_train_{log_suffix}.log'
        import contextlib
        model_name = model_path.name
        with open(train_log_path, 'w', encoding='utf-8') as logf:
            with contextlib.redirect_stdout(logf), contextlib.redirect_stderr(logf):
                model.train(data=str(yaml_path), epochs=epochs, project=str(project_dir), name='exp', exist_ok=True)
        self.log.info("学習ログを出力しました: %s (ベースモデル: %s)", train_log_path, model_name)

# DatasetPreparerクラスを削除し、main関数で直接エクスポート処理を行う
# --- DatasetPreparerクラス削除 ---
# --- AugmentationManager, ModelTrainerは残す ---

def main():
    parser = argparse.ArgumentParser(description='YOLO DataSetワンストップ生成・学習スクリプト')
    parser.add_argument('--input-json', type=str, required=True, help='入力JSONファイルのパス')
    parser.add_argument('--date-from', type=str, default=None, help='対象画像の日付範囲（開始）例: 20250601')
    parser.add_argument('--date-to', type=str, default=None, help='対象画像の日付範囲（終了）例: 20250610')
    parser.add_argument('--augment-num', type=int, default=20, help='各画像ごとのオーグメント拡張数（デフォルト20）')
    parser.add_argument('--epochs', type=int, default=100, help='YOLO学習のエポック数')
    parser.add_argument('--retrain-loops', type=int, default=1, help='再学習ループ回数（初回学習後に何回再学習するか）')
    parser.add_argument('--epoch-multiplier', type=int, default=2, help='再学習ごとのエポック数倍率')
    parser.add_argument('--retrain-mode', type=str, default='ask', choices=['ask', 'immediate', 'night'], help='再学習のタイミング: ask=都度確認, immediate=すぐ, night=夜間')
    parser.add_argument('--mode', type=str, default='all', choices=['all', 'augment'], help='"all"=全処理, "augment"=オーグメントのみ')
    parser.add_argument('--yolo-tmp-dir', type=str, default=None, help='既存YOLOデータセットディレクトリ（augmentモード用）')
    parser.add_argument('--augment-output-dir', type=str, default=None, help='オーグメント画像・ラベルの出力先ディレクトリ（augmentモード用）')
    parser.add_argument('--test-until', choices=['pretrain'], default=None, help='pretrain指定で学習前までテスト実行して終了')
    args = parser.parse_args()

    # 入力JSONのロードとログ出力
    input_json_path = Path(args.input_json)
    log.info(f"入力JSON: {input_json_path}")
    if not input_json_path.exists():
        log.error(f"指定された入力JSONが存在しません: {input_json_path}")
        sys.exit(1)
    try:
        with open(input_json_path, encoding="utf-8") as f:
            json_data = json.load(f)
        log.info(f"入力JSONの件数: {len(json_data) if isinstance(json_data, list) else 'dict'}")
    except Exception as e:
        log.error(f"入力JSONの読み込みに失敗: {e}")
        sys.exit(1)

    log.info("日付範囲: %s ～ %s", args.date_from, args.date_to)
    log.info("オーグメント拡張数: %d", args.augment_num)
    log.info("エポック数: %d", args.epochs)
    log.info("再学習ループ回数: %d", args.retrain_loops)
    log.info("エポック倍率: %d", args.epoch_multiplier)
    log.info("再学習タイミング: %s", args.retrain_mode)
    log.info("実行モード: %s", args.mode)

    db_path = Path(__file__).parent / 'src' / 'data' / 'model_training_cache.db'
    datasets_base = Path(__file__).parent / 'src' / 'datasets'
    model_path = Path(__file__).parent / 'src' / 'yolo' / 'yolo11n.pt'

    if args.mode == 'all':
        # --- YOLOデータセット生成クラスでDB登録のみ実施 ---
        from src.data.db_to_yolo_dataset import YoloDatasetBuilder
        # 既存DBを初期化（削除）
        if db_path.exists():
            db_path.unlink()
        # DBテーブルを初期化
        from src.data.json_to_db import create_table, clear_tables, insert_from_json, JSON_PATH
        create_table(db_path=db_path)
        clear_tables(db_path=db_path)
        # 入力JSONをDBへ登録
        import shutil
        tmp_json_path = Path(db_path).parent / 'input_tmp.json'
        shutil.copy2(str(input_json_path), str(tmp_json_path))
        # JSON_PATHを書き換えてinsert_from_jsonを呼ぶ
        import src.data.json_to_db as json_to_db_mod
        json_to_db_mod.JSON_PATH = tmp_json_path
        json_to_db_mod.DB_PATH = db_path
        insert_from_json()
        tmp_json_path.unlink(missing_ok=True)
        # --- YOLOデータセット生成クラスでDB登録のみ実施 ---
        from src.data.db_to_yolo_dataset import YoloDatasetBuilder
        builder = YoloDatasetBuilder(out_dir=None, db_path=db_path)
        builder.process()  # ここでDB登録まで完結
        # DB登録後にラベル付き画像が0件なら即エラー終了
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM bboxes")
        n_labeled = c.fetchone()[0]
        conn.close()
        if n_labeled == 0:
            log.error('[ALL] DB登録後にラベル付き画像が0件です。データセット生成を中止します')
            sys.exit(1)
        # --- AugmentationManagerで作業ディレクトリ生成＆拡張 ---
        model_trainer = ModelTrainer(log)
        aug_db_path = db_path  # DBはそのまま使い回す
        from src.utils.yolo_dataset_exporter import YoloDatasetExporter
        final_dir = datasets_base / f'yolo_final_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}'
        final_dir.mkdir(parents=True, exist_ok=True)
        # DB→final_dirへ直接エクスポート
        yolo_exporter = YoloDatasetExporter(output_dir=str(final_dir), val_ratio=0.2, db_path=str(aug_db_path))
        yolo_exporter.export(force_flush=True)
        log.info(f'[EXPORT] DataSet書き出し: {final_dir} (DB: {aug_db_path})')
        # augment_managerはfinal_dirを入力、final_dir_augmentedを出力に使う
        augment_manager = AugmentationManager(log, model_trainer)
        final_dir_aug = Path(str(final_dir) + '_augmented')
        augment_manager.run_augmentation(final_dir, args.augment_num, final_dir_aug, aug_db_path)
        # --- 拡張画像・ラベルをDBに登録 ---
        from src.data.json_to_db import insert_from_yolo_dir
        insert_from_yolo_dir(final_dir_aug, db_path=aug_db_path)
        # --- DB登録件数を確認してログ出力 ---
        import sqlite3
        conn = sqlite3.connect(str(aug_db_path))
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM images")
        n_images = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM bboxes")
        n_bboxes = c.fetchone()[0]
        c.execute("SELECT COUNT(DISTINCT image_id) FROM bboxes")
        n_bbox_images = c.fetchone()[0]
        n_empty_label_images = n_images - n_bbox_images
        conn.close()
        log.info(f"[DEBUG] insert_from_yolo_dir直後: imagesテーブル件数={n_images}, bboxesテーブル件数={n_bboxes}, bbox付き画像数={n_bbox_images}, 空ラベル画像数={n_empty_label_images}")
        # --- 異常スキップ率チェック ---
        if n_images == 0 or n_bbox_images == 0 or n_bbox_images < 0.5 * n_images:
            log.error(
                f"[ABORT] オーグメント拡張後のbbox付き画像数が異常に少ないため後続処理を中止します "
                f"(bbox付き画像数={n_bbox_images}, images={n_images}, augment_num={args.augment_num})"
            )
            sys.exit(1)  # 重大な異常時は処理を終了

        # --- DBから新しいディレクトリへエクスポート ---
        # エクスポート先の新しいディレクトリを作成
        export_target_dir_base_name = f'yolo_exported_augmented_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}'
        export_target_dir = datasets_base / export_target_dir_base_name
        export_target_dir.mkdir(parents=True, exist_ok=True) 

        log.info(f"[EXPORT_NEW_DIR] オーグメント済みDBから新しいディレクトリへエクスポートします: {export_target_dir}")
        
        yolo_exporter_final = YoloDatasetExporter(output_dir=str(export_target_dir), val_ratio=0.2, db_path=str(aug_db_path))
        yolo_exporter_final.export(force_flush=True) # 新しいディレクトリにエクスポート
        log.info(f"[EXPORT_NEW_DIR] DataSet書き出し(拡張後・新ディレクトリ): {export_target_dir} (DB: {aug_db_path})")
        
        from src.data.validate_db_bboxes import validate_bboxes_in_db
        validate_bboxes_in_db(aug_db_path) # DBのバリデーション

        # yaml_path と project_dir も新しいエクスポート先ディレクトリ内のものを使用
        yaml_path = export_target_dir / 'dataset.yaml'
        project_dir = export_target_dir / 'train_run' # 学習結果はこの中に保存される
        
        labels_train_dir = export_target_dir / 'labels' / 'train'
        labels_val_dir = export_target_dir / 'labels' / 'val'
        
        def count_nonempty_label_files(d: Path) -> int:
            if not d.exists():
                return 0
            return sum(1 for f in d.glob('*.txt') if f.stat().st_size > 0)
        n_train = count_nonempty_label_files(labels_train_dir)
        n_val = count_nonempty_label_files(labels_val_dir)
        log.info("[ALL] 拡張後データセット: trainラベル数(空でない): %d, valラベル数(空でない): %d", n_train, n_val)
        if n_train == 0 or n_val == 0:
            log.warning('[ALL] 拡張後データセット: trainまたはvalのラベルが0件のため、YOLO学習をスキップします')
        else:
            # --- 学習前に孤立ラベル(画像欠損)チェックを実施 ---
            def _remove_orphan_labels(label_dir: Path, img_split_dir: Path):
                removed = 0
                if label_dir.exists():
                    for lbl_file in label_dir.glob('*.txt'):
                        img_file = img_split_dir / (lbl_file.stem + '.jpg')
                        if not img_file.exists():
                            try:
                                lbl_file.unlink()
                                removed += 1
                            except Exception:
                                pass
                return removed

            removed_train = _remove_orphan_labels(labels_train_dir, export_target_dir / 'images' / 'train')
            removed_val = _remove_orphan_labels(labels_val_dir, export_target_dir / 'images' / 'val')
            if removed_train or removed_val:
                log.warning('[CLEANUP] 孤立ラベルファイルを削除しました: train=%d, val=%d', removed_train, removed_val)

            model_trainer.train(yaml_path, args.epochs, project_dir, model_path)
            log.info('[ALL] 拡張後データセットの学習結果: %s', project_dir)
            log.info('[ALL] 拡張後データセットの学習ログ: logs/04_train_%s.log', model_path.stem.replace('.', '_'))
            log.info('[ALL] 拡張後データセットでのYOLO学習が完了しました')

        return
    elif args.mode == 'augment':
        from src.augment.runner import main as augment_main
        from src.data.json_to_db import create_table, clear_tables
        if args.yolo_tmp_dir:
            dataset_dir = Path(args.yolo_tmp_dir)
        else:
            yolo_dirs = sorted([d for d in datasets_base.glob('yolo_dataset_all_*') if d.is_dir()], reverse=True)
            if not yolo_dirs:
                log.error('[ERROR] augmentモード: YOLOデータセットディレクトリが見つかりません。--yolo-tmp-dirで指定してください。')
                sys.exit(1)
            dataset_dir = yolo_dirs[0]
            log.info(f'[INFO] augmentモード: 最新のYOLOデータセットディレクトリを自動選択: {dataset_dir}')
        if args.augment_output_dir:
            output_dir = Path(args.augment_output_dir)
        else:
            output_dir = dataset_dir.parent / 'yolo_augmented'
        db_path = output_dir / 'model_training_cache.db'
        db_path.parent.mkdir(parents=True, exist_ok=True)
        import shutil
        if db_path.exists():
            db_path.unlink()
        create_table(db_path=db_path)
        clear_tables(db_path=db_path)
        log.info(f'[INFO] augment用DBを初期化: {db_path}')
        summary = augment_main(dataset_dir, n=args.augment_num, output_dir=output_dir, show_progress=True, return_summary=True, db_path=db_path)
        log.info(f'[INFO] オーグメント拡張完了: {output_dir}')
        log.info(f'[INFO] augmentサマリー: {summary}')
        log.info('[INFO] augmentモードのため、以降のtrain/val分割・学習処理はスキップします')
        return
    else:
        log.error(f'[ERROR] 未知のmode: {args.mode}')
        sys.exit(1)

if __name__ == '__main__':
    main()