"""ProjectManagerDialog: YOLOデータセット管理用ダイアログ"""
import sys
import os
import shutil
import subprocess
import traceback
from PyQt6.QtCore import QTimer, QThread, Qt, QSize
from PyQt6.QtGui import QPixmap, QPainter, QPen, QIcon
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QMessageBox, QInputDialog,
    QFileDialog, QTableWidget, QTableWidgetItem, QLabel, QTextEdit, QApplication, QFrame, QLineEdit, QProgressBar, QComboBox, QWidget, QSpinBox
)
from ..utils.managed_files_utils import save_current_managed_files, switch_managed_file_set
from ..yolo_dataset_exporter import YoloDatasetExporter
from ..utils.path_manager import path_manager
from ..utils.model_selector import get_available_models
from .thumb_widget import ThumbWorker
from .image_list_with_bbox_widget import ImageListWithBboxWidget
from ..image_preview_dialog import ImagePreviewDialog
from .project_list_panel import ProjectListPanel
import json
import yaml
import glob
from ..utils.image_ops import convert_image_to_yolo_dataset, augment_image_dataset
from ..utils.scan_dataset_regen import regen_scan_for_images_dataset
from ..utils.data_augmenter import augment_dataset
from ..utils.yolo_e2e_pipeline import run_yolo_e2e_pipeline

class ProjectManagerDialog(QDialog):
    """プロジェクト管理ダイアログ"""
    def __init__(self, managed_base_dir, parent=None, test_mode=False):
        super().__init__(parent)
        self.setWindowTitle("プロジェクト管理")
        self.managed_base_dir = managed_base_dir
        self.test_mode = test_mode
        self._setup_ui()
        self.refresh_model_combo()
        self.refresh_dataset_path()

    def _setup_ui(self):
        vbox = QVBoxLayout(self)
        self.setLayout(vbox)
        # --- プロジェクトリスト部分を分離 ---
        self.project_list_panel = ProjectListPanel(self.managed_base_dir, self)
        vbox.addWidget(self.project_list_panel)
        self.list_widget = self.project_list_panel.list_widget  # 既存ロジック互換のため
        # --- 右クリックメニュー追加 ---
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.on_project_list_context_menu)
        # --- クラス比較表示欄 ---
        self.class_compare_edit = QTextEdit()
        self.class_compare_edit.setReadOnly(True)
        self.class_compare_edit.setPlaceholderText("元JSONロール/ラベル・YOLOクラス・差分")
        vbox.addWidget(self.class_compare_edit)
        # --- プロジェクト選択用OK/キャンセルボタン ---
        hbox_btn = QHBoxLayout()
        self.ok_btn = QPushButton("選択")
        self.cancel_btn = QPushButton("キャンセル")
        hbox_btn.addWidget(self.ok_btn)
        hbox_btn.addWidget(self.cancel_btn)
        vbox.addLayout(hbox_btn)
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        # --- ワンストップ用エポック数指定 ---
        hbox_onestop = QHBoxLayout()
        self.onestop_epochs_spin = QSpinBox()
        self.onestop_epochs_spin.setRange(1, 1000)
        self.onestop_epochs_spin.setValue(5)
        hbox_onestop.addWidget(QLabel("ワンストップ学習エポック数:"))
        hbox_onestop.addWidget(self.onestop_epochs_spin)
        self.onestop_btn = QPushButton("ワンストップE2E実行")
        hbox_onestop.addWidget(self.onestop_btn)
        self.onestop_btn.clicked.connect(self.on_one_stop_workflow)
        vbox.addLayout(hbox_onestop)
        # --- ① データセット作成 ---
        vbox.addWidget(QLabel("① データセット作成"))
        hbox_ds = QHBoxLayout()
        self.ds_output_edit = QLineEdit()
        self.ds_output_edit.setPlaceholderText("出力先ディレクトリ")
        self.ds_output_btn = QPushButton("参照")
        self.ds_create_btn = QPushButton("データセット作成")
        hbox_ds.addWidget(self.ds_output_edit)
        hbox_ds.addWidget(self.ds_output_btn)
        hbox_ds.addWidget(self.ds_create_btn)
        vbox.addLayout(hbox_ds)
        self.ds_progress = QProgressBar()
        self.ds_progress.setVisible(False)
        vbox.addWidget(self.ds_progress)
        self.ds_result = QTextEdit()
        self.ds_result.setReadOnly(True)
        vbox.addWidget(self.ds_result)
        vbox.addWidget(QFrame(frameShape=QFrame.Shape.HLine))
        # --- データセットサマリー表示欄 ---
        self.dataset_summary_edit = QTextEdit()
        self.dataset_summary_edit.setReadOnly(True)
        self.dataset_summary_edit.setPlaceholderText("データセットサマリー（画像数・bbox数・クラス種など）")
        vbox.addWidget(self.dataset_summary_edit)
        # --- ② データ拡張 ---
        vbox.addWidget(QLabel("② データ拡張"))
        hbox_aug = QHBoxLayout()
        self.aug_input_edit = QLineEdit()
        self.aug_input_edit.setPlaceholderText("拡張元ディレクトリ")
        self.aug_output_edit = QLineEdit()
        self.aug_output_edit.setPlaceholderText("拡張出力先")
        self.aug_btn = QPushButton("拡張実行")
        hbox_aug.addWidget(self.aug_input_edit)
        hbox_aug.addWidget(self.aug_output_edit)
        hbox_aug.addWidget(self.aug_btn)
        vbox.addLayout(hbox_aug)
        self.aug_progress = QProgressBar()
        self.aug_progress.setVisible(False)
        vbox.addWidget(self.aug_progress)
        self.aug_result = QTextEdit()
        self.aug_result.setReadOnly(True)
        vbox.addWidget(self.aug_result)
        vbox.addWidget(QFrame(frameShape=QFrame.Shape.HLine))
        # --- ③ 学習 ---
        vbox.addWidget(QLabel("③ 学習"))
        hbox_train = QHBoxLayout()
        self.train_dataset_edit = QLineEdit()
        self.train_dataset_edit.setPlaceholderText("データセットyaml")
        self.train_model_combo = QComboBox()
        self.train_epochs_spin = QSpinBox()
        self.train_epochs_spin.setRange(1, 1000)
        self.train_epochs_spin.setValue(100)
        self.train_btn = QPushButton("学習開始")
        hbox_train.addWidget(self.train_dataset_edit)
        hbox_train.addWidget(self.train_model_combo)
        hbox_train.addWidget(self.train_epochs_spin)
        hbox_train.addWidget(self.train_btn)
        vbox.addLayout(hbox_train)
        self.train_progress = QProgressBar()
        self.train_progress.setVisible(False)
        vbox.addWidget(self.train_progress)
        self.train_eta_label = QLabel("残り推定: --:--:--")
        self.train_eta_label.setVisible(False)
        vbox.addWidget(self.train_eta_label)
        self.train_result = QTextEdit()
        self.train_result.setReadOnly(True)
        vbox.addWidget(self.train_result)
        # --- その他 ---
        hbox_other = QHBoxLayout()
        btn_path_manager = QPushButton("パスマネージャー管理")
        btn_model_test = QPushButton("モデル推論テスト")
        btn_bbox_preview = QPushButton("拡張前bboxサムネイル一覧")
        btn_bbox_preview_aug = QPushButton("拡張後bboxサムネイル一覧")
        btn_close = QPushButton("閉じる")
        for btn in [btn_path_manager, btn_model_test, btn_bbox_preview, btn_bbox_preview_aug, btn_close]:
            hbox_other.addWidget(btn)
        vbox.addLayout(hbox_other)
        btn_close.clicked.connect(self.reject)
        btn_path_manager.clicked.connect(self.open_path_manager)
        btn_model_test.clicked.connect(self.open_model_test_widget)
        btn_bbox_preview.clicked.connect(self.open_batch_bbox_preview)
        btn_bbox_preview_aug.clicked.connect(self.open_batch_bbox_preview_aug)
        # --- シグナル接続 ---
        self.ds_output_btn.clicked.connect(self.select_ds_output_dir)
        self.ds_create_btn.clicked.connect(self.create_yolo_dataset)
        self.aug_btn.clicked.connect(self.run_data_augmentation)
        self.train_btn.clicked.connect(self.run_yolo_training)
        self.list_widget.itemDoubleClicked.connect(self.show_project_json_detail)

    def select_ds_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "データセット出力先を選択")
        if dir_path:
            self.ds_output_edit.setText(dir_path)

    def create_yolo_dataset(self):
        # 仮: 選択プロジェクトのscan_for_images_dataset.jsonを使う
        selected_projects = self.get_selected_projects()
        if not selected_projects:
            QMessageBox.warning(self, "選択エラー", "データセット作成するプロジェクトを選択してください")
            return
        json_paths = self.get_yolo_json_paths(selected_projects)
        if not json_paths:
            QMessageBox.warning(self, "エラー", "画像リストJSONが見つかりません")
            return
        output_dir = self.ds_output_edit.text() or os.path.join(self.managed_base_dir, selected_projects[0], "yolo_dataset")
        self.ds_output_edit.setText(output_dir)
        self.ds_progress.setVisible(True)
        self.ds_progress.setRange(0, 0)
        # --- 元JSONのロール・ラベル一覧抽出 ---
        orig_roles = set()
        orig_labels = set()
        orig_classes = set()
        print(f"[DEBUG] json_paths: {json_paths}")
        for json_path in json_paths:
            try:
                print(f"[DEBUG] open: {json_path}")
                with open(json_path, 'r', encoding='utf-8') as f:
                    head = f.read(500)
                    print(f"[DEBUG] {json_path} head: {head[:200]}...")
                    f.seek(0)
                    data = json.load(f)
                if isinstance(data, list):
                    images = data
                elif isinstance(data, dict):
                    images = data.get('images', [])
                else:
                    images = []
                print(f"[DEBUG] images count: {len(images)}")
                for img in images[:3]:
                    print(f"[DEBUG] img keys: {list(img.keys())}")
                    bboxes = img.get('bboxes', [])
                    print(f"[DEBUG] bboxes count: {len(bboxes)}")
                    for bbox in bboxes[:3]:
                        print(f"[DEBUG] bbox: {bbox}")
                # 全件走査でクラス名抽出
                for img in images:
                    bboxes = img.get('bboxes', [])
                    for bbox in bboxes:
                        role = bbox.get('role')
                        label = bbox.get('label')
                        if role:
                            orig_roles.add(role)
                            orig_classes.add(role)
                        elif label:
                            orig_labels.add(label)
                            orig_classes.add(label)
            except Exception as e:
                print(f"[ERROR] JSON parse error: {json_path}: {e}")
        exporter = YoloDatasetExporter(json_paths, output_dir=output_dir)
        result = exporter.export(mode='all')
        self.ds_progress.setVisible(False)
        self.ds_result.setPlainText(f"出力先: {output_dir}\n除外画像数: {len(result.get('rejected', []))}")
        # 拡張元に自動セット
        self.aug_input_edit.setText(os.path.join(output_dir, "images", "train"))
        self.aug_output_edit.setText(os.path.join(self.managed_base_dir, selected_projects[0], "augmented_dataset"))
        self.train_dataset_edit.setText(os.path.join(output_dir, "dataset.yaml"))
        # --- データセットサマリー表示 ---
        self.show_dataset_summary(output_dir, yaml_path=os.path.join(output_dir, "dataset.yaml"))
        # --- YOLOクラス名リスト抽出 ---
        yolo_names = set()
        dataset_yaml = os.path.join(output_dir, "dataset.yaml")
        if dataset_yaml and os.path.exists(dataset_yaml):
            with open(dataset_yaml, 'r', encoding='utf-8') as f:
                ydata = yaml.safe_load(f)
            names = ydata.get('names')
            if isinstance(names, dict):
                yolo_names = set(names.values())
            elif isinstance(names, list):
                yolo_names = set(names)
        # --- 差分計算 ---
        removed_roles = orig_roles - yolo_names
        removed_labels = orig_labels - yolo_names
        removed_classes = orig_classes - yolo_names
        added_yolo = yolo_names - orig_classes
        msg = (
            f"元ロール: {sorted(orig_roles)}\n"
            f"元ラベル: {sorted(orig_labels)}\n"
            f"元クラス（role優先,なければlabel）: {sorted(orig_classes)}\n"
            f"YOLOクラス: {sorted(yolo_names)}\n"
            f"\n[差分]\n"
            f"YOLOに残らなかったロール: {sorted(removed_roles)}\n"
            f"YOLOに残らなかったラベル: {sorted(removed_labels)}\n"
            f"YOLOに残らなかったクラス: {sorted(removed_classes)}\n"
            f"YOLOで新規追加: {sorted(added_yolo)}"
        )
        self.class_compare_edit.setPlainText(msg)
        # --- ここから拡張処理を自動実行 ---
        src_img_dir = os.path.join(output_dir, "images", "train")
        src_label_dir = os.path.join(output_dir, "labels", "train")
        dst_dir = os.path.join(self.managed_base_dir, selected_projects[0], "augmented_dataset")
        self.aug_progress.setVisible(True)
        self.aug_progress.setRange(0, 0)
        try:
            aug_result = augment_dataset(
                src_img_dir=src_img_dir,
                src_label_dir=src_label_dir,
                dst_dir=dst_dir,
                n_augment=5
            )
            aug_msg = (
                f"拡張元: {src_img_dir}\n"
                f"ラベル: {src_label_dir}\n"
                f"拡張先: {dst_dir}\n"
                f"元画像数: {aug_result.get('original_images', '?')}\n"
                f"拡張画像数: {aug_result.get('augmented_images', '?')}\n"
                f"合計画像数: {aug_result.get('total_images', '?')}\n"
                f"dataset.yaml: {aug_result.get('yaml_file', '')}"
            )
            self.aug_result.setPlainText(aug_msg)
            self.show_dataset_summary(dst_dir, yaml_path=os.path.join(dst_dir, "dataset.yaml"))
        except Exception as e:
            self.aug_result.setPlainText(f"拡張処理中にエラー: {e}")
        self.aug_progress.setVisible(False)
        self.train_dataset_edit.setText(os.path.join(dst_dir, "dataset.yaml"))

    def guess_label_dir_from_img_dir(self, img_dir):
        # 例: /path/to/xxx/images/train → /path/to/xxx/labels/train
        img_dir = os.path.abspath(img_dir)
        parent, last = os.path.split(img_dir)
        if os.path.basename(parent) == "images":
            label_dir = os.path.join(os.path.dirname(parent), "labels", last)
        else:
            label_dir = img_dir.replace(os.sep + "images" + os.sep, os.sep + "labels" + os.sep)
        if not os.path.exists(label_dir):
            # fallback: /path/to/xxx/labels
            label_dir = os.path.join(os.path.dirname(parent), "labels")
        return label_dir

    def run_data_augmentation(self):
        from ..utils.data_augmenter import augment_dataset
        src_img_dir = self.aug_input_edit.text()
        dst_dir = self.aug_output_edit.text()
        if not os.path.exists(src_img_dir):
            QMessageBox.warning(self, "エラー", f"拡張元ディレクトリが存在しません: {src_img_dir}")
            return
        src_label_dir = self.guess_label_dir_from_img_dir(src_img_dir)
        if not os.path.exists(src_label_dir):
            QMessageBox.warning(self, "エラー", f"ラベルディレクトリが存在しません: {src_label_dir}")
            return
        self.aug_progress.setVisible(True)
        self.aug_progress.setRange(0, 0)
        # augment_datasetを直接呼び出し、結果を取得
        try:
            result = augment_dataset(
                src_img_dir=src_img_dir,
                src_label_dir=src_label_dir,
                dst_dir=dst_dir,
                n_augment=2
            )
            msg = (
                f"拡張元: {src_img_dir}\n"
                f"ラベル: {src_label_dir}\n"
                f"拡張先: {dst_dir}\n"
                f"元画像数: {result.get('original_images', '?')}\n"
                f"拡張画像数: {result.get('augmented_images', '?')}\n"
                f"合計画像数: {result.get('total_images', '?')}\n"
                f"dataset.yaml: {result.get('yaml_file', '')}"
            )
            self.aug_result.setPlainText(msg)
            # --- 拡張後データセットサマリー表示 ---
            self.show_dataset_summary(dst_dir, yaml_path=os.path.join(dst_dir, "dataset.yaml"))
        except Exception as e:
            self.aug_result.setPlainText(f"拡張処理中にエラー: {e}")
        self.aug_progress.setVisible(False)
        # 学習用データセットパスに自動セット
        self.train_dataset_edit.setText(os.path.join(dst_dir, "dataset.yaml"))

    def refresh_model_combo(self):
        """YOLOモデル（標準・学習済み）を自動リストアップ（パスマネージャー統一）"""
        self.train_model_combo.clear()
        for name, path in get_available_models():
            self.train_model_combo.addItem(name, path)

    def refresh_dataset_path(self):
        """既存のdataset.yamlを自動セット（優先順位: 拡張済み→通常）"""
        base_dirs = ["augmented_dataset", "yolo_dataset"]
        for d in base_dirs:
            dataset_yaml = os.path.join(self.managed_base_dir, "current", d, "dataset.yaml")
            if os.path.exists(dataset_yaml):
                self.train_dataset_edit.setText(dataset_yaml)
                return
        # どちらもなければ空
        self.train_dataset_edit.setText("")

    def run_yolo_training(self):
        import threading
        self.refresh_model_combo()
        self.refresh_dataset_path()
        dataset_yaml = self.train_dataset_edit.text()
        model_idx = self.train_model_combo.currentIndex()
        model_path = self.train_model_combo.itemData(model_idx) if model_idx >= 0 else None
        epochs = self.train_epochs_spin.value()
        # dataset.yamlのクラス名バリデーション
        class_names = []
        if dataset_yaml and os.path.exists(dataset_yaml):
            try:
                with open(dataset_yaml, 'r', encoding='utf-8') as f:
                    ydata = yaml.safe_load(f)
                names = ydata.get('names')
                if isinstance(names, dict):
                    class_names = list(names.values())
                elif isinstance(names, list):
                    class_names = names
                else:
                    class_names = []
            except Exception as e:
                QMessageBox.warning(self, "エラー", f"dataset.yamlの読み込みに失敗: {e}")
                return
        if not dataset_yaml or not os.path.exists(dataset_yaml):
            QMessageBox.warning(self, "エラー", f"データセットyamlが存在しません: {dataset_yaml}")
            return
        if not model_path or not os.path.exists(model_path):
            QMessageBox.warning(self, "エラー", f"モデルファイルが存在しません: {model_path}")
            return
        if not class_names:
            QMessageBox.warning(self, "エラー", f"dataset.yamlにクラス名（names）が定義されていません。学習できません。")
            self.train_result.setPlainText(f"dataset.yaml: {dataset_yaml}\nモデル: {model_path}\n[警告] クラス名リストが空です")
            return
        msg = (
            f"学習データセット: {dataset_yaml}\n"
            f"モデル: {model_path}\n"
            f"エポック数: {epochs}\n"
            f"クラス名リスト: {class_names}"
        )
        self.train_progress.setVisible(True)
        self.train_progress.setRange(0, 0)
        self.train_result.setPlainText(msg)

        # --- Python APIでYOLO学習を実行し、print出力をフックして表示 ---
        def run_train():
            import sys
            import io
            import re
            import time
            try:
                from ultralytics import YOLO
                model = YOLO(model_path)
                # printをフック
                dialog_self = self
                start_time = time.time()
                total_epochs = epochs
                def update_progress(epoch):
                    elapsed = time.time() - start_time
                    progress = int(100 * epoch / total_epochs)
                    self.train_progress.setValue(progress)
                    self.train_progress.setVisible(True)
                    self.train_eta_label.setVisible(True)
                    if epoch > 0:
                        eta = elapsed / epoch * (total_epochs - epoch)
                        eta_str = time.strftime('%H:%M:%S', time.gmtime(eta))
                        self.train_eta_label.setText(f"残り推定: {eta_str}")
                    else:
                        self.train_eta_label.setText("残り推定: --:--:--")
                class PrintHook(io.StringIO):
                    def __init__(self, dialog):
                        super().__init__()
                        self.dialog = dialog
                    def write(self, s):
                        super().write(s)
                        for line in s.rstrip().splitlines():
                            self.dialog.train_result.append(line)
                            m = re.search(r"Epoch (\d+)/(\d+)", line)
                            if m:
                                epoch = int(m.group(1))
                                update_progress(epoch)
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = sys.stderr = PrintHook(dialog_self)
                try:
                    results = model.train(data=dataset_yaml, epochs=epochs, imgsz=640, batch=8, device='cpu', verbose=True)
                    self.train_result.append("[学習完了]")
                except Exception as e:
                    self.train_result.append(f"[例外] 学習中にエラー: {e}")
                finally:
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                self.train_progress.setVisible(False)
                self.train_eta_label.setVisible(False)
            except Exception as e:
                self.train_result.append(f"[例外] 学習プロセス実行中にエラー: {e}")
                self.train_progress.setVisible(False)
                self.train_eta_label.setVisible(False)
        threading.Thread(target=run_train, daemon=True).start()

    def refresh_list(self):
        self.project_list_panel.refresh_list()

    def get_selected_projects(self):
        return self.project_list_panel.get_selected_projects()

    def on_switch(self):
        """プロジェクト切り替え"""
        names = self.get_selected_projects()
        if not names:
            QMessageBox.warning(self, "選択エラー", "プロジェクトを選択してください")
            return
        set_dir = os.path.join(self.managed_base_dir, names[0])
        try:
            switch_managed_file_set(set_dir)
            self.accept()
        except OSError as exc:
            QMessageBox.critical(self, "エラー", f"切り替え中にエラー: {exc}")

    def on_new(self):
        """新規プロジェクト作成"""
        name, ok = QInputDialog.getText(self, "新規プロジェクト", "プロジェクト名を入力:")
        if ok and name:
            new_dir = os.path.join(self.managed_base_dir, name)
            if os.path.exists(new_dir):
                QMessageBox.warning(self, "エラー", "同名のプロジェクトが既に存在します")
                return
            try:
                save_current_managed_files(self.managed_base_dir)
                shutil.copytree(os.path.join(self.managed_base_dir, "current"), new_dir)
                self.refresh_list()
            except OSError as exc:
                QMessageBox.critical(self, "エラー", f"新規作成中にエラー: {exc}")

    def on_copy(self):
        """プロジェクト複写"""
        names = self.get_selected_projects()
        if not names:
            QMessageBox.warning(self, "選択エラー", "複写元プロジェクトを選択してください")
            return
        new_name, ok = QInputDialog.getText(
            self, "プロジェクト複写", f"{names[0]} を複写して新しいプロジェクト名を入力:")
        if ok and new_name:
            src_dir = os.path.join(self.managed_base_dir, names[0])
            dst_dir = os.path.join(self.managed_base_dir, new_name)
            if os.path.exists(dst_dir):
                QMessageBox.warning(self, "エラー", "同名のプロジェクトが既に存在します")
                return
            try:
                shutil.copytree(src_dir, dst_dir)
                self.refresh_list()
            except OSError as exc:
                QMessageBox.critical(self, "エラー", f"複写中にエラー: {exc}")

    def on_delete(self):
        """プロジェクト削除"""
        names = self.get_selected_projects()
        if not names:
            QMessageBox.warning(self, "選択エラー", "削除するプロジェクトを選択してください")
            return
        if names[0] == "current":
            QMessageBox.warning(self, "エラー", "currentは削除できません")
            return
        ret = QMessageBox.question(
            self, "確認", f"{names[0]} を本当に削除しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if ret == QMessageBox.StandardButton.Yes:
            try:
                shutil.rmtree(os.path.join(self.managed_base_dir, names[0]))
                self.refresh_list()
            except OSError as exc:
                QMessageBox.critical(self, "エラー", f"削除中にエラー: {exc}")

    def get_yolo_json_paths(self, selected_projects):
        """選択プロジェクトからYOLO出力対象のJSONパスリストを返す"""
        return [
            os.path.join(
                self.managed_base_dir,
                name,
                "scan_for_images_dataset.json"
            )
            for name in selected_projects
            if os.path.exists(
                os.path.join(
                    self.managed_base_dir,
                    name,
                    "scan_for_images_dataset.json"
                )
            )
        ]

    def run_yolo_export(self, json_paths, export_dir, mode_key, existing_dir):
        """YOLOデータセットエクスポート実行"""
        exporter = YoloDatasetExporter(json_paths, output_dir=export_dir)
        result = exporter.export(mode=mode_key, existing_dataset_dir=existing_dir)
        return exporter, result

    def show_labeling_result_dialog(self, exporter, result):
        """ラベリング結果ダイアログを表示"""
        all_results = self._collect_labeling_results(exporter, result)
        sorted_results = self._sort_labeling_results(all_results)
        self._show_labeling_result_table(sorted_results)

    def _collect_labeling_results(self, exporter, result):
        """ラベリング結果を集約"""
        all_results = []
        for img_path in exporter.images:
            anns = exporter.annotations.get(str(img_path), [])
            if anns:
                labels = []
                for ann in anns:
                    role = ann.get('role')
                    label = ann.get('label')
                    class_name = role if role else label
                    box = ann.get('box')
                    labels.append(f"{class_name}: {box}")
                all_results.append((str(img_path), "OK", ", ".join(labels)))
            else:
                all_results.append((str(img_path), "ラベル（バウンディングボックス）が無い", ""))
        for img_path, reason in result.get("rejected", []):
            for i, (img, _, labels) in enumerate(all_results):
                if img == str(img_path):
                    all_results[i] = (img, reason, labels)
        return all_results

    def _sort_labeling_results(self, all_results):
        """OK/NGでソート"""
        ok_list = [r for r in all_results if r[1] == "OK"]
        ng_list = [r for r in all_results if r[1] != "OK"]
        return ok_list + ng_list

    def _show_labeling_result_table(self, sorted_results):
        """ラベリング結果テーブルをダイアログ表示"""
        result_dialog = QDialog(self)
        result_dialog.setWindowTitle("YOLOラベリング結果一覧")
        result_dialog.resize(1200, 800)
        result_dialog.setWindowFlag(
            result_dialog.windowFlags() |
            result_dialog.windowFlags().MaximizeUsingFullscreenGeometryHint,
            True
        )
        vbox = QVBoxLayout(result_dialog)
        table = QTableWidget(len(sorted_results), 3)
        table.setHorizontalHeaderLabels(["画像", "結果", "ラベル内容"])
        for i, (img, status, labels) in enumerate(sorted_results):
            parent = os.path.basename(os.path.dirname(img))
            fname = os.path.basename(img)
            short_path = f"{parent}/{fname}" if parent else fname
            table.setItem(i, 0, QTableWidgetItem(str(short_path)))
            table.setItem(i, 1, QTableWidgetItem(str(status)))
            table.setItem(i, 2, QTableWidgetItem(str(labels)))
            table.item(i, 0).setData(256, img)
        vbox.addWidget(QLabel("全画像のラベリング結果（OK=正常/それ以外は除外理由）"))
        vbox.addWidget(table)
        table.resizeColumnsToContents()
        table.horizontalHeader().setStretchLastSection(True)
        table.setColumnWidth(2, 400)
        def on_table_double_clicked(row, _col):
            """テーブルのダブルクリックで画像プレビュー"""
            img_path = table.item(row, 0).data(256)
            if not img_path or not os.path.exists(img_path):
                return
            json_path = os.path.splitext(img_path)[0] + ".json"
            if not os.path.exists(json_path):
                cache_dir = os.path.join(
                    os.path.dirname(__file__), "..", "..", "src", "image_preview_cache"
                )
                base = os.path.basename(img_path)
                for fname in os.listdir(cache_dir) if os.path.exists(cache_dir) else []:
                    if fname.endswith('.json') and base in fname:
                        json_path = os.path.join(cache_dir, fname)
                        break
            try:
                pixmap = QPixmap(img_path) if os.path.exists(img_path) else None
                preview_dialog = ImagePreviewDialog(
                    img_path, result_dialog, pixmap=pixmap, json_path=json_path
                )
                if self.test_mode:
                    QTimer.singleShot(1000, preview_dialog.accept)
                preview_dialog.exec()
            except OSError as exc:
                traceback.print_exc()
                QMessageBox.warning(
                    result_dialog, "エラー", f"プレビュー表示に失敗: {exc}"
                )
        table.cellDoubleClicked.connect(on_table_double_clicked)
        btn = QPushButton("閉じる", result_dialog)
        btn.clicked.connect(result_dialog.accept)
        vbox.addWidget(btn)
        result_dialog.setLayout(vbox)
        if self.test_mode:
            QTimer.singleShot(2000, result_dialog.accept)
        result_dialog.exec()

    def on_export_yolo(self):
        """YOLOデータセット出力・ラベリング結果ダイアログ表示（分割版）"""
        config_path = os.path.join(self.managed_base_dir, "last_yolo_export_dir.json")
        selected_projects = self.get_selected_projects()
        if not selected_projects:
            QMessageBox.warning(self, "選択エラー", "YOLO出力するプロジェクトを選択してください（複数可）")
            return
        json_paths = self.get_yolo_json_paths(selected_projects)
        if not json_paths:
            QMessageBox.warning(self, "エラー", "選択したプロジェクトに画像リストJSONが見つかりません")
            return
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    _ = f.read()
            except OSError:
                pass
        export_dir = None
        mode, ok = QInputDialog.getItem(
            self, "出力モード選択", "全体出力 or 追加出力:", ["全体出力", "追加出力"], 0, False
        )
        if not ok:
            return
        mode_key = 'all' if mode == "全体出力" else 'add'
        existing_dir = None
        if mode_key == 'add':
            existing_dir = QFileDialog.getExistingDirectory(
                self, "既存YOLOデータセットディレクトリを選択"
            )
            if not existing_dir:
                return
        try:
            exporter, result = self.run_yolo_export(json_paths, export_dir, mode_key, existing_dir)
            try:
                with open(config_path, "w", encoding="utf-8") as f:
                    f.write(export_dir or "")
            except OSError:
                pass
            self.show_labeling_result_dialog(exporter, result)
        except OSError as exc:
            traceback.print_exc()
            QMessageBox.critical(self, "エラー", f"YOLOデータセット出力中にエラー: {exc}")

    def open_path_manager(self):
        """パスマネージャーダイアログを開く"""
        pm_dialog = PathManagerWidget(self)
        pm_dialog.exec()

    def open_yolo_workflow(self):
        """YOLO学習ワークフローウィンドウを開く"""
        from ..yolo_train_predict_manager import YoloWorkflowManager
        self.workflow_window = YoloWorkflowManager()
        self.workflow_window.show()
        self.workflow_window.setWindowModality(Qt.WindowModality.NonModal)

    def on_augment_yolo(self):
        """データ拡張ウィジェットを起動（ワークフロー用）"""
        from .data_augment_widget import DataAugmentWidget
        self.augment_window = DataAugmentWidget()
        self.augment_window.show()
        self.augment_window.setWindowModality(Qt.WindowModality.NonModal)

    def on_one_stop_workflow(self):
        from ..utils.yolo_e2e_pipeline import run_yolo_e2e_pipeline
        selected_projects = self.get_selected_projects()
        if not selected_projects:
            QMessageBox.warning(self, "選択エラー", "ワンストップ実行するプロジェクトを選択してください")
            return
        # scan_json, model_path, epochs, n_augmentをGUIから取得
        scan_json = os.path.join(self.managed_base_dir, selected_projects[0], "scan_for_images_dataset.json")
        model_idx = self.train_model_combo.currentIndex()
        model_path = self.train_model_combo.itemData(model_idx) if model_idx >= 0 else None
        epochs = self.onestop_epochs_spin.value()
        n_augment = 2
        output_dir = os.path.join(self.managed_base_dir, selected_projects[0], "yolo_e2e_output")
        self.train_result.clear()
        def gui_progress(msg):
            self.train_result.append(str(msg))
        import threading
        def run_e2e():
            try:
                result = run_yolo_e2e_pipeline(
                    scan_json=scan_json,
                    model_path=model_path,
                    epochs=epochs,
                    n_augment=n_augment,
                    output_dir=output_dir,
                    progress_callback=gui_progress
                )
                # --- best.ptを分かりやすい名前でmodels/にコピー ---
                import shutil
                import datetime
                from ..utils.path_manager import path_manager
                exp_dirs = glob.glob(os.path.join(os.getcwd(), "runs", "train", "exp*"))
                if exp_dirs:
                    latest_exp = max(exp_dirs, key=os.path.getmtime)
                    best_pt = os.path.join(latest_exp, "weights", "best.pt")
                    if os.path.exists(best_pt):
                        models_dir = path_manager.models_dir
                        models_dir.mkdir(parents=True, exist_ok=True)
                        dt = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        proj_name = os.path.basename(os.path.dirname(scan_json))
                        new_name = f"best_{proj_name}_{dt}.pt"
                        new_path = os.path.join(models_dir, new_name)
                        shutil.copy2(best_pt, new_path)
                        self.train_result.append(f"[E2E] best.ptを {new_path} に保存しました")
                self.train_result.append("[E2E] 完了")
                self.refresh_model_combo()
            except Exception as e:
                self.train_result.append(f"[E2E][ERROR] {e}")
        threading.Thread(target=run_e2e, daemon=True).start()

    def open_yolo_workflow_with_dataset(self, dataset_dir, epochs=None):
        """学習ウィジェットを自動起動し、データセットパスとエポック数を渡す（仮）"""
        from ..yolo_train_predict_manager import YoloWorkflowManager
        self.workflow_window = YoloWorkflowManager(dataset_dir=dataset_dir, epochs=epochs)
        self.workflow_window.show()
        self.workflow_window.setWindowModality(Qt.WindowModality.NonModal)

    def open_model_test_widget(self):
        from .model_test_widget import ModelTestWidget
        dlg = ModelTestWidget(self)
        dlg.exec()

    def show_project_json_detail(self, item):
        import json
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QScrollArea, QWidget, QGridLayout
        proj_name = item.text()
        json_path = os.path.join(self.managed_base_dir, proj_name, "scan_for_images_dataset.json")
        if not os.path.exists(json_path):
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "エラー", f"ファイルが存在しません: {json_path}")
            return
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            images = data
        elif isinstance(data, dict):
            images = data.get('images', [])
        else:
            images = []
        dlg = QDialog(self)
        dlg.setWindowTitle(f"{proj_name} の画像サムネイル＋bbox一覧")
        vbox = QVBoxLayout(dlg)
        scroll = QScrollArea(dlg)
        scroll.setWidgetResizable(True)
        container = QWidget()
        grid = QGridLayout(container)
        container.setLayout(grid)
        scroll.setWidget(container)
        vbox.addWidget(scroll)
        n_cols = 5
        thumb_size = 180
        # --- テンポラリ画像パスをダイアログ属性で管理 ---
        dlg._temp_img_paths = []
        def cleanup_temp_imgs():
            for p in getattr(dlg, '_temp_img_paths', []):
                if p and os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass
            dlg._temp_img_paths = []
        orig_accept = dlg.accept
        orig_reject = dlg.reject
        orig_close_event = dlg.closeEvent
        def on_accept():
            cleanup_temp_imgs()
            orig_accept()
        def on_reject():
            cleanup_temp_imgs()
            orig_reject()
        def closeEvent(event):
            cleanup_temp_imgs()
            orig_close_event(event)
        dlg.accept = on_accept
        dlg.reject = on_reject
        dlg.closeEvent = closeEvent
        # --- サムネイル生成をスレッド化 ---
        thumb_widgets = []
        from PyQt6.QtWidgets import QListWidgetItem
        from PyQt6.QtGui import QIcon, QPixmap
        from PyQt6.QtCore import Qt
        worker = ThumbWorker(images, dlg)
        thread = QThread(dlg)
        worker.moveToThread(thread)
        worker.thumb_ready.connect(lambda idx, img_path, temp_img_path, bbox_objs, roles: None)  # 一時的にダミー処理
        thread.started.connect(worker.run)
        thread.start()
        # ダイアログ終了時にスレッドを安全に停止
        def stop_thread():
            if thread.isRunning():
                thread.quit()
                thread.wait()
        dlg.finished.connect(stop_thread)
        close_btn = QPushButton("閉じる", dlg)
        close_btn.clicked.connect(dlg.accept)
        vbox.addWidget(close_btn)
        dlg.setLayout(vbox)
        dlg.resize(1100, 800)
        dlg.exec()

    def show_dataset_summary(self, base_dir, label_dir_name="labels/train", img_dir_name="images/train", yaml_path=None):
        from collections import Counter
        base_dir = os.path.abspath(base_dir)
        label_dir = os.path.join(base_dir, label_dir_name)
        img_dir = os.path.join(base_dir, img_dir_name)
        img_files = glob.glob(os.path.join(img_dir, "*.jpg")) + glob.glob(os.path.join(img_dir, "*.png"))
        label_files = glob.glob(os.path.join(label_dir, "*.txt"))
        bbox_count = 0
        class_ids = []
        for lf in label_files:
            try:
                with open(lf, 'r', encoding='utf-8') as f:
                    for line in f:
                        parts = line.strip().split()
                        if parts:
                            class_ids.append(int(parts[0]))
                            bbox_count += 1
            except Exception:
                pass
        class_id_counter = Counter(class_ids)
        names = []
        if yaml_path and os.path.exists(yaml_path):
            try:
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    ydata = yaml.safe_load(f)
                n = ydata.get('names')
                if isinstance(n, dict):
                    names = [v for k, v in sorted(n.items())]
                elif isinstance(n, list):
                    names = n
            except Exception:
                pass
        msg = (
            f"画像数: {len(img_files)}\n"
            f"ラベルファイル数: {len(label_files)}\n"
            f"全bbox数: {bbox_count}\n"
            f"クラス種: {len(set(class_ids))} 件: {[names[i] if i < len(names) else i for i in sorted(set(class_ids))]}\n"
            f"クラスID件数: {dict(class_id_counter)}\n"
            f"dataset.yaml names: {names}\n"
            f"\n--- サンプル ---\n"
            f"画像: {img_files[:3]}\n"
            f"ラベル: {label_files[:3]}\n"
        )
        self.dataset_summary_edit.setPlainText(msg)

    def open_batch_bbox_preview(self):
        # 直近のyolo_datasetディレクトリを自動推定
        img_dir = os.path.join(self.managed_base_dir, "current", "yolo_dataset", "images", "train")
        label_dir = os.path.join(self.managed_base_dir, "current", "yolo_dataset", "labels", "train")
        if not (os.path.exists(img_dir) and os.path.exists(label_dir)):
            QMessageBox.warning(self, "エラー", f"{img_dir} または {label_dir} が存在しません")
            return
        dlg = BatchBboxPreviewDialog(img_dir, label_dir, parent=self)
        dlg.exec()

    def open_batch_bbox_preview_aug(self):
        img_dir = os.path.join(self.managed_base_dir, "current", "augmented_dataset", "images")
        label_dir = os.path.join(self.managed_base_dir, "current", "augmented_dataset", "labels")
        if not (os.path.exists(img_dir) and os.path.exists(label_dir)):
            QMessageBox.warning(self, "エラー", f"{img_dir} または {label_dir} が存在しません")
            return
        dlg = BatchBboxPreviewDialog(img_dir, label_dir, parent=self)
        dlg.exec()

    def on_project_list_context_menu(self, pos):
        from PyQt6.QtWidgets import QMenu
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        menu = QMenu(self.list_widget)
        act_regen = menu.addAction("中央リスト（scan_for_images_dataset.json）再生成")
        action = menu.exec(self.list_widget.mapToGlobal(pos))
        if action == act_regen:
            import glob
            import json
            project_name = item.text()
            managed_base = path_manager.src_dir.parent / "managed_files"
            project_dir = managed_base / project_name
            # 共通ロジック呼び出し
            result = regen_scan_for_images_dataset(str(project_dir), debug=True)
            msg = (
                f"scan_for_images_dataset.jsonを再生成します。\n"
                f"[集計対象]\n"
                f"キャッシュ: {result['cache_dir']} （{len(result['cache_jsons'])}件）\n"
                f"image_path有効: {result['pred_output']}件\n"
                f"実在ファイル: {result['exist_count']}件\n"
                f"image_path未設定/不正: {result['none_count']}件\n"
                f"予測出力件数: {result['pred_output']}件\n"
                f"\nよろしいですか？"
            )
            ret = QMessageBox.question(self, "再生成確認", msg, QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
            if ret != QMessageBox.StandardButton.Ok:
                return
            # 再生成後サマリー
            if result['regen_ok']:
                QMessageBox.information(self, "再生成完了", f"{result['out_path']} を再生成しました{result['summary_msg']}")
            else:
                QMessageBox.warning(self, "再生成失敗", f"{result['out_path']} の再生成に失敗しました")

    def show_project_json_detail_by_path(self, json_path, proj_name):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout
        if not os.path.exists(json_path):
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "エラー", f"ファイルが存在しません: {json_path}")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(f"{proj_name} の画像サムネイル＋bbox一覧")
        vbox = QVBoxLayout(dlg)
        widget = ImageListWithBboxWidget(None, None, dlg)
        vbox.addWidget(widget)
        dlg.setLayout(vbox)
        dlg.resize(1100, 800)
        dlg.exec()

    def accept(self):
        # 選択中のプロジェクトJSONファイルパスを取得
        sel_items = self.list_widget.selectedItems()
        if not sel_items:
            QMessageBox.warning(self, "選択エラー", "プロジェクトを選択してください")
            return
        sel_text = sel_items[0].text()
        # ファイル名部分だけ抽出
        fname = sel_text.split(' [')[0]
        json_path = os.path.join(self.managed_base_dir, fname)
        self.selected_project_json_path = json_path
        super().accept()

# --- タブ用ウィジェット定義 ---
class DatasetExportTab(QWidget):
    def __init__(self, parent, project_manager):
        super().__init__(parent)
        self.project_manager = project_manager
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("データセット出力"))
        self.export_btn = QPushButton("YOLOデータセット出力")
        layout.addWidget(self.export_btn)
        self.setLayout(layout)
        self.export_btn.clicked.connect(self.on_export_yolo)

    def on_export_yolo(self):
        self.project_manager.on_export_yolo()

class AugmentTab(QWidget):
    def __init__(self, parent, project_manager):
        super().__init__(parent)
        self.project_manager = project_manager
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("データ拡張"))
        self.augment_btn = QPushButton("データ拡張")
        layout.addWidget(self.augment_btn)
        self.setLayout(layout)
        self.augment_btn.clicked.connect(self.on_augment_yolo)

    def on_augment_yolo(self):
        self.project_manager.on_augment_yolo()

class TrainTab(QWidget):
    def __init__(self, parent, project_manager):
        super().__init__(parent)
        self.project_manager = project_manager
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("YOLO学習"))
        self.train_btn = QPushButton("YOLO学習ワークフロー")
        layout.addWidget(self.train_btn)
        self.setLayout(layout)
        self.train_btn.clicked.connect(self.on_train)

    def on_train(self):
        self.project_manager.open_yolo_workflow()

class PathManagerWidget(QDialog):
    """パスマネージャー管理ファイル一覧ダイアログ"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("パスマネージャー管理ファイル一覧")
        vbox = QVBoxLayout(self)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["キー", "説明", "パス", "状態"])
        vbox.addWidget(self.table)
        self.text = QTextEdit(self)
        self.text.setReadOnly(True)
        vbox.addWidget(QLabel("ファイル内容プレビュー:"))
        vbox.addWidget(self.text)
        btn_hbox = QHBoxLayout()
        btn_open = QPushButton("ファイルを開く")
        btn_mark_unused = QPushButton("いらないとしてマーク")
        btn_close = QPushButton("閉じる")
        for btn in [btn_open, btn_mark_unused, btn_close]:
            btn_hbox.addWidget(btn)
        vbox.addLayout(btn_hbox)
        self.setLayout(vbox)
        btn_open.clicked.connect(self.open_file)
        btn_mark_unused.clicked.connect(self.mark_unused)
        btn_close.clicked.connect(self.reject)
        self.table.cellClicked.connect(self.on_cell_clicked)
        self.unused_keys = set()
        self.refresh_table()

    def refresh_table(self):
        """テーブルを最新の状態に更新"""
        files = path_manager.get_json_files_with_description()
        self.table.setRowCount(len(files))
        for i, (key, info) in enumerate(files.items()):
            self.table.setItem(i, 0, QTableWidgetItem(key))
            self.table.setItem(i, 1, QTableWidgetItem(info["description"]))
            self.table.setItem(i, 2, QTableWidgetItem(str(info["path"])))
            state = "いらない" if key in self.unused_keys else "OK"
            self.table.setItem(i, 3, QTableWidgetItem(state))

    def on_cell_clicked(self, row, _col):
        """セルクリック時にファイル内容をプレビュー"""
        path = self.table.item(row, 2).text()
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
            self.text.setPlainText(content)
        except OSError as e:
            self.text.setPlainText(f"読み込みエラー: {e}")

    def open_file(self):
        """選択ファイルをOS標準アプリで開く"""
        row = self.table.currentRow()
        if row < 0:
            return
        path = self.table.item(row, 2).text()
        try:
            if sys.platform.startswith('win'):
                os.startfile(path)
            elif sys.platform.startswith('darwin'):
                with subprocess.Popen(['open', path]):
                    pass
            else:
                with subprocess.Popen(['xdg-open', path]):
                    pass
        except OSError as e:
            QMessageBox.warning(self, "エラー", f"ファイルを開けません: {e}")

    def mark_unused(self):
        """選択ファイルを「いらない」としてマーク"""
        row = self.table.currentRow()
        if row < 0:
            return
        key = self.table.item(row, 0).text()
        self.unused_keys.add(key)
        self.refresh_table()

class BatchBboxPreviewDialog(QDialog):
    def __init__(self, img_dir, label_dir, parent=None):
        super().__init__(parent)
        self.setWindowTitle("バッチBboxプレビュー")
        vbox = QVBoxLayout(self)
        # 画像リスト＋bboxウィジェットを使う
        # 画像リストJSONの自動推定（YOLO形式前提）
        # ここではimg_dir/label_dirからscan_for_images_dataset.jsonを推定しないので、
        # 画像ディレクトリ内の画像を全て表示
        widget = ImageListWithBboxWidget(None, None, self)
        widget.list_widget.clear()
        # 画像ファイル一覧取得
        import glob
        img_paths = []
        for ext in ("*.jpg", "*.jpeg", "*.png", "*.bmp"):  # 必要に応じて拡張
            img_paths.extend(glob.glob(os.path.join(img_dir, ext)))
        for img_path in img_paths:
            # bboxファイル（YOLO形式）を探す
            base = os.path.splitext(os.path.basename(img_path))[0]
            label_path = os.path.join(label_dir, base + ".txt")
            bbox_objs = []
            if os.path.exists(label_path):
                with open(label_path, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            # YOLO形式: class x_center y_center w h
                            try:
                                class_id = int(parts[0])
                                x, y, w, h = map(float, parts[1:5])
                                bbox_objs.append({"x": x, "y": y, "w": w, "h": h, "class_id": class_id})
                            except Exception:
                                pass
            widget.add_thumb(0, img_path, img_path, bbox_objs, [])
        vbox.addWidget(widget)
        btn = QPushButton("閉じる", self)
        btn.clicked.connect(self.accept)
        vbox.addWidget(btn)
        self.setLayout(vbox)
