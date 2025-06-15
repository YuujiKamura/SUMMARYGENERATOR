import sys
print("DEBUG: Script execution started at the very beginning", file=sys.stderr)
# --- OpenCV警告・stderr抑制 ---
def _suppress_cv2_warnings() -> None:
    try:
        import cv2, contextlib, io
        print("DEBUG: cv2 imported in _suppress_cv2_warnings", file=sys.stderr) # 追加
        if hasattr(cv2, "setLogLevel"):
            with contextlib.redirect_stderr(io.StringIO()):
                cv2.setLogLevel(3)  # 3 = ERROR
            print("DEBUG: cv2.setLogLevel(3) called", file=sys.stderr) # 追加
    except ImportError:
        print("DEBUG: cv2 import failed in _suppress_cv2_warnings", file=sys.stderr) # 追加
        pass  # OpenCV 未導入なら無視
    print("DEBUG: _suppress_cv2_warnings finished", file=sys.stderr) # 追加

print("DEBUG: Calling _suppress_cv2_warnings()", file=sys.stderr) # 追加
_suppress_cv2_warnings()
print("DEBUG: _suppress_cv2_warnings() called", file=sys.stderr) # 追加

import argparse
print("DEBUG: argparse imported", file=sys.stderr) # 追加
from pathlib import Path
print("DEBUG: pathlib.Path imported", file=sys.stderr) # 追加
import datetime
print("DEBUG: datetime imported", file=sys.stderr) # 追加
import json
print("DEBUG: json imported", file=sys.stderr) # 追加
import logging
print("DEBUG: logging imported", file=sys.stderr) # 追加
from typing import List, Dict, Any, Optional # Optional を追加
print("DEBUG: typing imported", file=sys.stderr) # 追加

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

    def train(self, yaml_path: str, epochs: int, project_dir: str, model_path: Optional[str] = None) -> Optional[Path]: # 型ヒントを修正
        try:
            from ultralytics import YOLO
        except ImportError:
            self.log.error('ultralyticsパッケージがインストールされていません。pip install ultralytics でインストールしてください。')
            return None
        from pathlib import Path
        
        project_dir_path = Path(project_dir)
        project_dir_path.mkdir(parents=True, exist_ok=True)

        current_model_path_to_use: Path
        if model_path is None:
            initial_model_path = Path(__file__).parent / 'src' / 'yolo' / 'yolo11n.pt'
            current_model_path_to_use = initial_model_path
            model_name_for_log = initial_model_path.name
            self.log.info(f"初期モデル {initial_model_path} から学習を開始します。")
        else:
            model_path_obj = Path(model_path)
            if not model_path_obj.exists():
                self.log.error(f"指定されたモデルパスが存在しません: {model_path_obj}")
                initial_model_path = Path(__file__).parent / 'src' / 'yolo' / 'yolo11n.pt'
                current_model_path_to_use = initial_model_path
                model_name_for_log = initial_model_path.name
                self.log.warning(f"フォールバックして初期モデル {initial_model_path} から学習を開始します。")
            else:
                current_model_path_to_use = model_path_obj
                model_name_for_log = model_path_obj.name
                self.log.info(f"モデル {model_path_obj} を使って学習を再開または継続します。")
        
        model_to_train = YOLO(str(current_model_path_to_use))
        
        self.log.info(f"学習を開始します。進捗はターミナルに表示されます。結果は {project_dir_path / 'exp'} に保存されます。")
        results = model_to_train.train(data=str(yaml_path), epochs=epochs, project=str(project_dir_path), name='exp', exist_ok=True)
        
        # --- デバッグログ追加 ---
        self.log.info(f"DEBUG: results object: {results}")
        self.log.info(f"DEBUG: type(results): {type(results)}")
        if hasattr(results, 'save_dir'):
            self.log.info(f"DEBUG: hasattr(results, 'save_dir'): True")
            self.log.info(f"DEBUG: results.save_dir: {results.save_dir}")
            self.log.info(f"DEBUG: type(results.save_dir): {type(results.save_dir)}")
        else:
            self.log.info(f"DEBUG: hasattr(results, 'save_dir'): False")
            # resultsオブジェクトの全属性を調べる
            if results:
                self.log.info(f"DEBUG: results attributes: {dir(results)}")
        # --- デバッグログ追加ここまで ---
        
        self.log.info(f"学習が完了しました。 (ベースモデル: {model_name_for_log})")
        
        # 新しいUltralyticsバージョンでは、保存先が project_dir/exp/weights/ になる
        # resultsオブジェクトのsave_dirプロパティが利用できない場合の対応
        expected_weights_dir = project_dir_path / 'exp' / 'weights'
        expected_best_model = expected_weights_dir / 'best.pt'
        expected_last_model = expected_weights_dir / 'last.pt'
        
        self.log.info(f"DEBUG: 期待される保存先: {expected_weights_dir}")
        self.log.info(f"DEBUG: best.pt存在チェック: {expected_best_model.exists()}")
        self.log.info(f"DEBUG: last.pt存在チェック: {expected_last_model.exists()}")
        
        if results and hasattr(results, 'save_dir') and results.save_dir:
            # resultsからsave_dirが取得できる場合
            save_dir_path = Path(str(results.save_dir))
            self.log.info(f"DEBUG: results.save_dirから取得: {save_dir_path}")
        else:
            # save_dirが取得できない場合は期待される場所を使用
            save_dir_path = project_dir_path / 'exp'
            self.log.info(f"DEBUG: デフォルト保存先を使用: {save_dir_path}")
        
        trained_model_path = save_dir_path / 'weights' / 'best.pt'
        if trained_model_path.exists():
            self.log.info(f"学習済みモデルが保存されました: {trained_model_path}")
            return trained_model_path
        else:
            self.log.warning(f"学習済みモデル best.pt が見つかりませんでした。保存先: {save_dir_path}")
            last_model_path = save_dir_path / 'weights' / 'last.pt'
            if last_model_path.exists():
                self.log.info(f"学習済みモデル last.pt を使用します: {last_model_path}")
                return last_model_path
            else:
                self.log.error(f"学習済みモデル last.pt も見つかりませんでした。")
                # 最後の手段として、期待される場所をチェック
                if expected_best_model.exists():
                    self.log.info(f"期待される場所でbest.ptを発見: {expected_best_model}")
                    return expected_best_model
                elif expected_last_model.exists():
                    self.log.info(f"期待される場所でlast.ptを発見: {expected_last_model}")
                    return expected_last_model
                else:
                    return None

# DatasetPreparerクラスを削除し、main関数で直接エクスポート処理を行う
# --- DatasetPreparerクラス削除 ---
# --- AugmentationManager, ModelTrainerは残す ---

def main():
    print("DEBUG: main() function started", file=sys.stderr) # デバッグ出力追加
    parser = argparse.ArgumentParser(description='YOLO DataSetワンストップ生成・学習スクリプト')
    parser.add_argument('--input-json', type=str, required=True, help='入力JSONファイルのパス')
    parser.add_argument('--date-from', type=str, default=None, help='対象画像の日付範囲（開始）例: 20250601')
    parser.add_argument('--date-to', type=str, default=None, help='対象画像の日付範囲（終了）例: 20250610')
    parser.add_argument('--augment-num', type=int, default=20, help='各画像ごとのオーグメント拡張数（デフォルト20）')
    parser.add_argument('--epochs', type=int, default=100, help='YOLO学習のエポック数')
    parser.add_argument('--retrain-epochs', type=int, default=30, help='ハードエグザンプル再学習のエポック数')
    parser.add_argument('--retrain-loops', type=int, default=1, help='再学習ループ回数（初回学習後に何回再学習するか）')
    parser.add_argument('--retrain-mode', type=str, default='ask', choices=['ask', 'immediate', 'night'], help='再学習のタイミング: ask=都度確認, immediate=すぐ, night=夜間')
    parser.add_argument('--mode', type=str, default='all', choices=['all', 'augment'], help='"all"=全処理, "augment"=オーグメントのみ')
    parser.add_argument('--yolo-tmp-dir', type=str, default=None, help='既存YOLOデータセットディレクトリ（augmentモード用）')
    parser.add_argument('--augment-output-dir', type=str, default=None, help='オーグメント画像・ラベルの出力先ディレクトリ（augmentモード用）')
    parser.add_argument('--test-until', choices=['pretrain'], default=None, help='pretrain指定で学習前までテスト実行して終了')
    args = parser.parse_args()
    print(f"DEBUG: args: {args}", file=sys.stderr) # デバッグ出力追加

    # --- グローバルパス設定 ---
    script_dir = Path(__file__).parent
    db_path = script_dir / 'src' / 'data' / 'model_training_cache.db'
    datasets_base_dir = script_dir / 'src' / 'datasets'
    initial_model_path_str = str(script_dir / 'src' / 'yolo' / 'yolo11n.pt') # ModelTrainerへはstrで渡す
    logs_dir = script_dir / 'logs' # logs_dir をここで定義
    logs_dir.mkdir(parents=True, exist_ok=True) # logsディレクトリがなければ作成

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
    log.info("再学習エポック数: %d", args.retrain_epochs)
    log.info("再学習ループ回数: %d", args.retrain_loops)
    log.info("再学習タイミング: %s", args.retrain_mode)
    log.info("実行モード: %s", args.mode)

    model_trainer = ModelTrainer(log) # ModelTrainerをここで初期化

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
        final_dir = datasets_base_dir / f'yolo_final_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}'
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
        export_target_dir_base_name = f'yolo_exported_augmented_img{n_bbox_images}_ep{args.epochs}_ag{args.augment_num}_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}'
        export_target_dir = datasets_base_dir / export_target_dir_base_name
        export_target_dir.mkdir(parents=True, exist_ok=True)
        
        yolo_exporter_final = YoloDatasetExporter(output_dir=str(export_target_dir), val_ratio=0.2, db_path=str(db_path)) # aug_db_path を db_path に修正
        # export()メソッドは data.yaml のパスを返すように YoloDatasetExporter側を修正する必要がある
        dataset_yaml_path_or_dict = yolo_exporter_final.export(force_flush=True) 
        
        dataset_yaml_path: Optional[str] = None
        if isinstance(dataset_yaml_path_or_dict, dict) and 'yaml_path' in dataset_yaml_path_or_dict:
            dataset_yaml_path = str(dataset_yaml_path_or_dict['yaml_path'])
        elif isinstance(dataset_yaml_path_or_dict, (str, Path)):
            dataset_yaml_path = str(dataset_yaml_path_or_dict)
        else:
            log.error(f"YoloDatasetExporter.export() から予期しない戻り値の型: {type(dataset_yaml_path_or_dict)}")
            sys.exit(1)

        log.info(f"[EXPORT] 最終DataSet書き出し: {export_target_dir} (DB: {db_path}), YAML: {dataset_yaml_path}")

        if not dataset_yaml_path or not Path(dataset_yaml_path).exists():
            log.error(f"データセットのYAMLファイルが見つかりません: {dataset_yaml_path}")
            sys.exit(1)

        # --- 学習実行 ---
        current_model_to_train_str: Optional[str] = initial_model_path_str # 初回学習は初期モデルから
        
        training_project_dir = logs_dir / f"training_run_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        trained_model_path_obj = model_trainer.train(
            yaml_path=str(dataset_yaml_path), 
            epochs=args.retrain_epochs, 
            project_dir=str(training_project_dir),
            model_path=current_model_to_train_str
        )
        if not trained_model_path_obj:
            log.error("初回学習に失敗しました。処理を終了します。")
            sys.exit(1)
        
        current_model_to_train_str = str(trained_model_path_obj) # 次の再学習ループのために更新

        # --- 再学習ループ（ハードエグザンプル方式） ---
        if args.retrain_loops > 0:
            for loop in range(args.retrain_loops):
                log.info(f"[RETRAIN] 再学習ループ {loop+1}/{args.retrain_loops} (hard-example mining) 開始")

                # 1) 推論＋食い違い画像収集
                hard_example_export_dir = datasets_base_dir / f"yolo_hard_example_loop{loop+1}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                try:
                    mis_count = collect_mis_detect_images(
                        model_path=current_model_to_train_str,
                        dataset_dir=export_target_dir,
                        output_dir=hard_example_export_dir,
                    )
                except Exception as e:
                    log.error(f"[RETRAIN] hard-example mining でエラー発生: {e}")
                    break

                if mis_count == 0:
                    log.info(f"[RETRAIN] ループ {loop+1}: ミス検出が0件のため再学習を終了します")
                    break

                retrain_yaml_path = hard_example_export_dir / "data.yaml"
                if not retrain_yaml_path.exists():
                    log.error(f"[RETRAIN] data.yaml が見つかりません: {retrain_yaml_path}")
                    break

                # 2) 再学習
                retrain_project_dir = logs_dir / f"retraining_run_loop{loop+1}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

                trained_model_path_after_retrain_obj = model_trainer.train(
                    yaml_path=str(retrain_yaml_path),
                    epochs=args.retrain_epochs,
                    project_dir=str(retrain_project_dir),
                    model_path=current_model_to_train_str,
                )

                if not trained_model_path_after_retrain_obj:
                    log.error(f"[RETRAIN] 再学習ループ {loop+1} に失敗しました。")
                    break

                current_model_to_train_str = str(trained_model_path_after_retrain_obj)
                log.info(f"[RETRAIN] 再学習ループ {loop+1}/{args.retrain_loops} 完了。モデル更新済み: {current_model_to_train_str}")

        log.info(f"全ての処理が完了しました。最終モデル: {current_model_to_train_str}")

    elif args.mode == 'augment':
        # --- augmentモード: 既存のYOLOデータセットディレクトリを使って拡張のみ実施 ---
        if args.yolo_tmp_dir and args.augment_output_dir:
            model_trainer = ModelTrainer(log)
            augment_manager = AugmentationManager(log, model_trainer)
            db_path = Path(__file__).parent / 'src' / 'data' / 'model_training_cache.db'
            augment_manager.run_augmentation(
                input_dir=Path(args.yolo_tmp_dir),
                augment_num=args.augment_num,
                output_dir=Path(args.augment_output_dir),
                db_path=db_path
            )
            log.info(f"[AUGMENT] 拡張完了: {args.augment_output_dir}")
        else:
            log.error("augmentモードでは --yolo-tmp-dir と --augment-output-dir の両方が必要です。")
            sys.exit(1)

if __name__ == "__main__":
    main()