# YOLO学習ウィジェット（PhotoCategorizerからコピー）
#!/usr/bin/env python3
"""
YOLO学習ウィジェット
"""
from pathlib import Path
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout, QPushButton, QSpinBox, QLineEdit, QFileDialog, QMessageBox, QListWidget, QLabel, QComboBox
)
from PyQt6.QtCore import pyqtSignal, QSettings, Qt
import yaml
from .common import create_model_combo, create_progress_bar, create_log_text

class YoloTrainWidget(QWidget):
    """YOLO学習用のウィジェット。モデル・データセット・エポック数等を指定し、学習処理を開始できる。"""
    training_started = pyqtSignal(str, str, int, str)

    def __init__(self, settings_manager=None, parent=None):
        """初期化"""
        super().__init__(parent)
        self.settings = QSettings("PhotoCategorizer", "YoloTrainPredictManager")
        self.settings_manager = settings_manager
        self._setup_ui()

    def _setup_ui(self):
        """UI初期化"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        train_group = QGroupBox("トレーニング設定")
        train_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        train_form = QFormLayout()
        train_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        train_form.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        train_form.setHorizontalSpacing(16)
        train_form.setVerticalSpacing(8)
        self.model_combo = create_model_combo(self)
        self.model_refresh_btn = QPushButton("更新")
        self.model_refresh_btn.setFixedWidth(60)
        self.model_refresh_btn.clicked.connect(self.refresh_models)
        model_layout = QHBoxLayout()
        model_layout.addWidget(self.model_combo, 1)
        model_layout.addWidget(self.model_refresh_btn)
        self.dataset_combo = QComboBox()
        self.dataset_refresh_btn = QPushButton("更新")
        self.dataset_refresh_btn.setFixedWidth(60)
        self.dataset_refresh_btn.clicked.connect(self.refresh_datasets)
        self.dataset_file_btn = QPushButton("ファイルから選択")
        self.dataset_file_btn.setFixedWidth(100)
        self.dataset_file_btn.clicked.connect(self.select_dataset_file)
        dataset_layout = QHBoxLayout()
        dataset_layout.addWidget(self.dataset_combo, 1)
        dataset_layout.addWidget(self.dataset_refresh_btn)
        dataset_layout.addWidget(self.dataset_file_btn)
        self.epochs_spin = QSpinBox()
        self.epochs_spin.setRange(1, 1000)
        self.epochs_spin.setValue(100)
        self.epochs_spin.setFixedWidth(80)
        self.exp_name_edit = QLineEdit("exp")
        train_form.addRow("モデル:", model_layout)
        train_form.addRow("データセット:", dataset_layout)
        train_form.addRow("エポック数:", self.epochs_spin)
        train_form.addRow("実験名:", self.exp_name_edit)
        train_group.setLayout(train_form)
        self.train_btn = QPushButton("トレーニング開始")
        self.train_btn.setMinimumHeight(40)
        self.train_btn.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.train_btn.clicked.connect(self.start_training)
        self.cancel_btn = QPushButton("キャンセル")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setFixedWidth(100)
        self.cancel_btn.clicked.connect(self.cancel_training)
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.train_btn)
        btn_layout.addWidget(self.cancel_btn)
        self.progress_bar = create_progress_bar(self)
        self.progress_bar.setFixedHeight(18)
        self.log_text = create_log_text(self)
        self.log_text.setMinimumHeight(120)
        self.label_list = QListWidget()
        self.label_list.setFixedHeight(100)
        layout.addWidget(train_group)
        layout.addLayout(btn_layout)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.log_text)
        layout.addWidget(QLabel("ラベル一覧:"))
        layout.addWidget(self.label_list)
        layout.addStretch(1)
        self.dataset_combo.currentIndexChanged.connect(self.update_label_list)
        self.refresh_models()
        self.refresh_datasets()
        last_dataset = self.settings.value("last_dataset_path", "")
        if last_dataset:
            for i in range(self.dataset_combo.count()):
                if self.dataset_combo.itemData(i) == last_dataset:
                    self.dataset_combo.setCurrentIndex(i)
                    break
        self.update_label_list()

    def refresh_models(self):
        """利用可能なYOLOモデルを更新"""
        self.model_combo.clear()
        combo = create_model_combo(self)
        for i in range(combo.count()):
            self.model_combo.addItem(combo.itemText(i), combo.itemData(i))

    def refresh_datasets(self):
        """利用可能なYOLOデータセットを更新"""
        self.dataset_combo.clear()
        dataset_dirs = [
            Path.cwd() / "dataset",
            Path.cwd() / "datasets"
        ]
        for dataset_dir in dataset_dirs:
            if not dataset_dir.exists():
                continue
            for yaml_file in dataset_dir.glob("**/dataset.yaml"):
                rel_path = yaml_file.relative_to(Path.cwd())
                self.dataset_combo.addItem(str(rel_path), str(yaml_file))

    def select_dataset_file(self):
        """ファイルダイアログでdataset.yamlを選択し、リストに追加"""
        file_path, _ = QFileDialog.getOpenFileName(self, "データセットYAMLを選択", str(Path.cwd()), "YAML Files (*.yaml)")
        if file_path:
            for i in range(self.dataset_combo.count()):
                if self.dataset_combo.itemData(i) == file_path:
                    self.dataset_combo.setCurrentIndex(i)
                    self.settings.setValue("last_dataset_path", file_path)
                    return
            self.dataset_combo.addItem(str(Path(file_path).relative_to(Path.cwd())), file_path)
            self.dataset_combo.setCurrentIndex(self.dataset_combo.count() - 1)
            self.settings.setValue("last_dataset_path", file_path)

    def start_training(self):
        """トレーニング処理を開始"""
        if self.model_combo.count() == 0:
            QMessageBox.warning(self, "エラー", "モデルが見つかりません")
            return
        if self.dataset_combo.count() == 0:
            QMessageBox.warning(self, "エラー", "データセットが見つかりません")
            return
        model_data = self.model_combo.currentData()
        model_path = model_data
        dataset_yaml = self.dataset_combo.currentData()
        epochs = self.epochs_spin.value()
        exp_name = self.exp_name_edit.text()
        self.train_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.log_text.clear()
        self.training_started.emit(model_path, dataset_yaml, epochs, exp_name)

    def on_training_output(self, msg):
        """学習進捗出力"""
        print(msg)
        try:
            with open("train_progress.log", "a", encoding="utf-8") as log_file:
                log_file.write(msg + "\n")
        except OSError as err:
            print(f"[LOGファイル書き込みエラー] {err}")

    def on_training_finished(self, return_code, result):
        """学習完了時の処理"""
        msg = f"[TRAIN_FINISHED] return_code={return_code}, result={result}"
        print(msg)
        try:
            with open("train_progress.log", "a", encoding="utf-8") as log_file:
                log_file.write(msg + "\n")
        except OSError as err:
            print(f"[LOGファイル書き込みエラー] {err}")
        if hasattr(super(), 'on_training_finished'):
            super().on_training_finished(return_code, result)

    def cancel_training(self):
        """学習キャンセル処理"""
        if hasattr(self, 'train_thread') and self.train_thread is not None:
            self.train_thread.stop()
        self.log_text.append("キャンセル要求を送信しました")
        self.cancel_btn.setEnabled(False)

    def get_current_dataset(self):
        """現在選択されているデータセットのパスを取得"""
        current = self.dataset_combo.currentData()
        if current:
            self.settings.setValue("last_dataset_path", current)
        return current

    def update_label_list(self):
        """選択中のデータセットのラベル一覧を表示"""
        self.label_list.clear()
        dataset_yaml = self.dataset_combo.currentData()
        if not dataset_yaml or not os.path.exists(dataset_yaml):
            return
        try:
            with open(dataset_yaml, "r", encoding="utf-8") as yaml_file:
                data = yaml.safe_load(yaml_file)
            names = data.get("names") or data.get("labels")
            if isinstance(names, dict):
                for key, value in names.items():
                    self.label_list.addItem(f"{key}: {value}")
            elif isinstance(names, list):
                for idx, value in enumerate(names):
                    self.label_list.addItem(f"{idx}: {value}")
        except (OSError, yaml.YAMLError) as err:
            self.label_list.addItem(f"ラベル取得エラー: {err}")
