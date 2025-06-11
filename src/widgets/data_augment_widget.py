#!/usr/bin/env python3
"""
データ拡張ウィジェット
"""
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QFormLayout, QLineEdit, QPushButton, 
    QHBoxLayout, QSpinBox, QFileDialog, QMessageBox
)
from PyQt6.QtCore import pyqtSignal
import yaml

class DataAugmentWidget(QWidget):
    """YOLOデータ拡張用のウィジェット。画像・ラベル・出力先・拡張数を指定し、拡張処理を開始できる。"""
    augmentation_started = pyqtSignal(str, str, str, int)
    augmentation_finished = pyqtSignal(int, object)  # return_code, result

    def __init__(self, settings_manager=None, parent=None):
        """初期化"""
        super().__init__(parent)
        self.settings = settings_manager
        self._setup_ui()

    def _setup_ui(self):
        """UI初期化"""
        layout = QVBoxLayout(self)
        augment_group = QGroupBox("データ拡張設定")
        augment_form = QFormLayout(augment_group)
        self.src_img_edit = QLineEdit()
        self.src_img_btn = QPushButton("選択...")
        self.src_img_btn.clicked.connect(self.select_src_img_dir)
        src_img_layout = QHBoxLayout()
        src_img_layout.addWidget(self.src_img_edit, 1)
        src_img_layout.addWidget(self.src_img_btn)
        self.src_label_edit = QLineEdit()
        self.src_label_btn = QPushButton("選択...")
        self.src_label_btn.clicked.connect(self.select_src_label_dir)
        src_label_layout = QHBoxLayout()
        src_label_layout.addWidget(self.src_label_edit, 1)
        src_label_layout.addWidget(self.src_label_btn)
        self.dst_dir_edit = QLineEdit("augmented_dataset")
        self.dst_dir_btn = QPushButton("選択...")
        self.dst_dir_btn.clicked.connect(self.select_dst_dir)
        dst_dir_layout = QHBoxLayout()
        dst_dir_layout.addWidget(self.dst_dir_edit, 1)
        dst_dir_layout.addWidget(self.dst_dir_btn)
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 20)
        self.count_spin.setValue(3)
        augment_form.addRow("元画像フォルダ:", src_img_layout)
        augment_form.addRow("元ラベルフォルダ:", src_label_layout)
        augment_form.addRow("出力フォルダ:", dst_dir_layout)
        augment_form.addRow("拡張バリエーション数:", self.count_spin)
        self.link_dataset_btn = QPushButton("データセットフォルダをリンク")
        self.link_dataset_btn.clicked.connect(self.link_dataset_folders)
        self.augment_btn = QPushButton("データ拡張開始")
        self.augment_btn.clicked.connect(self.start_data_augmentation)
        self.augment_btn.setMinimumHeight(40)
        layout.addWidget(augment_group)
        layout.addWidget(self.link_dataset_btn)
        layout.addWidget(self.augment_btn)

    def select_src_img_dir(self):
        """元画像フォルダ選択ダイアログ"""
        dir_path = QFileDialog.getExistingDirectory(self, "元画像フォルダを選択")
        if dir_path:
            self.src_img_edit.setText(dir_path)
            img_dir = Path(dir_path)
            if img_dir.name == "images":
                dataset_root = img_dir.parent
                label_dir = dataset_root / "labels"
                if label_dir.exists():
                    self.src_label_edit.setText(str(label_dir))

    def select_src_label_dir(self):
        """元ラベルフォルダ選択ダイアログ"""
        dir_path = QFileDialog.getExistingDirectory(self, "元ラベルフォルダを選択")
        if dir_path:
            self.src_label_edit.setText(dir_path)

    def select_dst_dir(self):
        """出力フォルダ選択ダイアログ"""
        dir_path = QFileDialog.getExistingDirectory(self, "出力フォルダを選択")
        if dir_path:
            self.dst_dir_edit.setText(dir_path)

    def link_dataset_folders(self):
        """YOLOデータセットのYAMLから画像・ラベル・出力先を自動セット"""
        dataset_yaml = self.window().get_current_dataset() if hasattr(self.window(), 'get_current_dataset') else None
        if not dataset_yaml:
            QMessageBox.warning(self, "警告", "先にデータセットを選択してください")
            return
        try:
            with open(dataset_yaml, 'r', encoding='utf-8') as yaml_file:
                dataset_config = yaml.safe_load(yaml_file)
            dataset_dir = Path(dataset_yaml).parent
            if "path" in dataset_config:
                dataset_dir = Path(dataset_config["path"])
            if "train" in dataset_config:
                train_path = dataset_config["train"]
                if isinstance(train_path, dict) and "images" in train_path:
                    images_dir = dataset_dir / train_path["images"]
                else:
                    images_dir = dataset_dir / train_path / "images"
            else:
                images_dir = dataset_dir / "images" / "train"
            if "train" in dataset_config and isinstance(dataset_config["train"], dict) and "labels" in dataset_config["train"]:
                labels_dir = dataset_dir / dataset_config["train"]["labels"]
            else:
                labels_dir = dataset_dir / "labels" / "train"
            output_dir = dataset_dir.parent / "augmented_dataset"
            if images_dir.exists():
                self.src_img_edit.setText(str(images_dir))
            if labels_dir.exists():
                self.src_label_edit.setText(str(labels_dir))
            self.dst_dir_edit.setText(str(output_dir))
        except (OSError, yaml.YAMLError) as err:
            QMessageBox.warning(self, "エラー", f"データセット構造の解析に失敗しました: {str(err)}")

    def start_data_augmentation(self):
        """データ拡張処理を開始"""
        src_img_dir = self.src_img_edit.text()
        src_label_dir = self.src_label_edit.text()
        dst_dir = self.dst_dir_edit.text()
        n_augment = self.count_spin.value()
        if not src_img_dir or not src_label_dir:
            QMessageBox.warning(self, "エラー", "元画像フォルダと元ラベルフォルダを選択してください")
            return
        self.augment_btn.setEnabled(False)
        self.augmentation_started.emit(src_img_dir, src_label_dir, dst_dir, n_augment)
        # augmentation_finished.emitは外部の拡張処理完了時に呼ぶ

    def on_augmentation_finished(self, return_code, result):
        """データ拡張完了時のUI復帰"""
        self.augment_btn.setEnabled(True) 