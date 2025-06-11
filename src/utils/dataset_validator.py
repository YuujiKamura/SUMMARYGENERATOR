#!/usr/bin/env python3
"""
データセットの検証を行うモジュール
"""
import os
from pathlib import Path
import yaml
from PyQt6.QtCore import QThread, pyqtSignal

class DatasetValidationThread(QThread):
    """データセットの整合性をチェックするスレッド"""
    output_received = pyqtSignal(str)
    validation_finished = pyqtSignal(bool, list)  # 成功かどうかとエラーリスト
    
    def __init__(self, yaml_path):
        super().__init__()
        self.yaml_path = yaml_path
        
    def run(self):
        """データセット検証の実行"""
        try:
            # YAMLファイルを読み込む
            self.output_received.emit(f"データセットYAMLを読み込み中: {self.yaml_path}")
            with open(self.yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            base = Path(self.yaml_path).parent
            errors = []
            warnings = []
            stats = {"train": {"images": 0, "labels": 0, "missing": 0},
                    "val": {"images": 0, "labels": 0, "missing": 0}}
            
            # クラス情報を取得
            class_names = data.get('names', {})
            self.output_received.emit(f"検出クラス: {len(class_names)}種類 ({', '.join(class_names.values()) if isinstance(class_names, dict) else class_names})")
            
            # トレーニングとバリデーションデータのパスを検証
            for split in ('train', 'val'):
                # YAML形式によって異なるパス指定方法に対応
                split_path = data.get(split)
                if not split_path:
                    errors.append(f"'{split}' のパス指定がYAMLファイルに見つかりません。")
                    continue
                
                # 絶対パスか相対パスか判定して処理
                if os.path.isabs(split_path):
                    img_dir = Path(split_path)
                else:
                    img_dir = (base / split_path).resolve()
                
                # 画像ディレクトリの存在確認
                if not img_dir.exists():
                    errors.append(f"{split} 画像ディレクトリが存在しません: {img_dir}")
                    continue
                
                # 推定されるラベルディレクトリ
                if 'labels' in str(img_dir):
                    lbl_dir = img_dir
                    img_dir = Path(str(img_dir).replace('labels', 'images'))
                else:
                    lbl_dir = Path(str(img_dir).replace('images', 'labels'))
                
                if not lbl_dir.exists():
                    errors.append(f"{split} ラベルディレクトリが存在しません: {lbl_dir}")
                    continue
                
                # 画像ファイルを取得
                img_files = list(img_dir.glob('*.jpg')) + list(img_dir.glob('*.jpeg')) + list(img_dir.glob('*.png'))
                stats[split]["images"] = len(img_files)
                
                if len(img_files) == 0:
                    warnings.append(f"{split}ディレクトリに画像ファイルが見つかりません: {img_dir}")
                    continue
                
                # 画像ファイルとラベルファイルの対応を確認
                missing_labels = []
                for img in img_files:
                    label_file = lbl_dir / f"{img.stem}.txt"
                    if not label_file.exists():
                        missing_labels.append(img.name)
                        stats[split]["missing"] += 1
                    else:
                        stats[split]["labels"] += 1
                
                if missing_labels:
                    if len(missing_labels) < 5:
                        errors.append(f"{split}セットで{len(missing_labels)}個の画像にラベルがありません: {', '.join(missing_labels)}")
                    else:
                        errors.append(f"{split}セットで{len(missing_labels)}個の画像にラベルがありません (最初の5つ: {', '.join(missing_labels[:5])}...)")
            
            # 統計情報の表示
            self.output_received.emit("\n--- データセットの統計情報 ---")
            for split in ('train', 'val'):
                self.output_received.emit(f"{split.capitalize()}セット: 画像 {stats[split]['images']}枚, ラベル {stats[split]['labels']}個, ラベル欠損 {stats[split]['missing']}個")
            
            # 警告とエラーの表示
            if warnings:
                self.output_received.emit("\n--- 警告 ---")
                for warning in warnings:
                    self.output_received.emit(f"・ {warning}")
            
            # 結果の判定
            if errors:
                self.output_received.emit("\n--- エラー ---")
                for error in errors:
                    self.output_received.emit(f"・ {error}")
                self.output_received.emit("\nデータセットの構造に問題があります。学習を開始する前に修正してください。")
                self.validation_finished.emit(False, errors)
            else:
                # 学習データの充分性チェック
                if stats["train"]["labels"] < 50:
                    self.output_received.emit(f"\n警告: 学習データが少なすぎます（{stats['train']['labels']}個のラベル）。少なくとも50〜100個のラベル付き画像を用意することをお勧めします。")
                
                self.output_received.emit("\nデータセットの構造は問題ありません。")
                self.validation_finished.emit(True, [])
                
        except Exception as e:
            self.output_received.emit(f"データセット検証中にエラーが発生しました: {str(e)}")
            self.validation_finished.emit(False, [str(e)])

    def validate_classify_dataset(self, dataset_dir: str) -> bool:
        """
        images/train, images/val配下のクラスディレクトリ・画像の有無のみチェック。
        dataset.yamlは無視。
        """
        import os
        for split in ["train", "val"]:
            split_dir = os.path.join(dataset_dir, split)
            if not os.path.isdir(split_dir):
                print(f"[ERROR] {split_dir} が存在しません")
                return False
            class_dirs = [d for d in os.listdir(split_dir) if os.path.isdir(os.path.join(split_dir, d))]
            if not class_dirs:
                print(f"[ERROR] {split_dir} にクラスディレクトリがありません")
                return False
            for class_dir in class_dirs:
                img_files = [f for f in os.listdir(os.path.join(split_dir, class_dir)) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
                if not img_files:
                    print(f"[ERROR] {split_dir}/{class_dir} に画像がありません")
                    return False
        print("[OK] classify用データセット構造バリデーションOK")
        return True 