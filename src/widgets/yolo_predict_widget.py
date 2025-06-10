# YOLO推論ウィジェット（PhotoCategorizerからコピー）
#!/usr/bin/env python3
"""
YOLO推論ウィジェット
"""
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QFormLayout, QLineEdit, QPushButton, 
    QHBoxLayout, QComboBox, QSpinBox, QFileDialog, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from .common import create_model_combo, create_progress_bar, create_log_text

class YoloPredictWidget(QWidget):
    """YOLO推論用のウィジェット。モデル・画像フォルダ・信頼度閾値を指定し、推論処理を開始できる。"""
    prediction_started = pyqtSignal(str, str, float)

    def __init__(self, settings_manager=None, parent=None):
        """初期化"""
        super().__init__(parent)
        self.settings = settings_manager
        self._setup_ui()

    def _setup_ui(self):
        """UI初期化"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        predict_group = QGroupBox("推論設定")
        predict_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        predict_form = QFormLayout()
        predict_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        predict_form.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        predict_form.setHorizontalSpacing(16)
        predict_form.setVerticalSpacing(8)
        self.model_combo = create_model_combo(self)
        self.model_refresh_btn = QPushButton("更新")
        self.model_refresh_btn.setFixedWidth(60)
        self.model_refresh_btn.clicked.connect(self.refresh_models)
        model_layout = QHBoxLayout()
        model_layout.setContentsMargins(0, 0, 0, 0)
        model_layout.setSpacing(8)
        model_layout.addWidget(self.model_combo)
        model_layout.addWidget(self.model_refresh_btn)
        model_widget = QWidget()
        model_widget.setLayout(model_layout)
        self.image_dir_edit = QLineEdit()
        self.image_dir_btn = QPushButton("選択...")
        self.image_dir_btn.setFixedWidth(80)
        self.image_dir_btn.clicked.connect(self.select_image_dir)
        image_dir_layout = QHBoxLayout()
        image_dir_layout.setContentsMargins(0, 0, 0, 0)
        image_dir_layout.setSpacing(8)
        image_dir_layout.addWidget(self.image_dir_edit)
        image_dir_layout.addWidget(self.image_dir_btn)
        image_dir_widget = QWidget()
        image_dir_widget.setLayout(image_dir_layout)
        self.conf_spin = QSpinBox()
        self.conf_spin.setRange(1, 100)
        self.conf_spin.setValue(25)
        self.conf_spin.setSuffix(" %")
        self.conf_spin.setFixedWidth(80)
        predict_form.addRow("モデル:", model_widget)
        predict_form.addRow("画像フォルダ:", image_dir_widget)
        predict_form.addRow("信頼度閾値:", self.conf_spin)
        predict_group.setLayout(predict_form)
        self.predict_btn = QPushButton("推論開始")
        self.predict_btn.setMinimumHeight(40)
        self.predict_btn.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.predict_btn.clicked.connect(self.start_prediction)
        self.progress_bar = create_progress_bar(self)
        self.progress_bar.setFixedHeight(18)
        self.log_text = create_log_text(self)
        self.log_text.setMinimumHeight(120)
        layout.addWidget(predict_group)
        layout.addWidget(self.predict_btn)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.log_text)
        layout.addStretch(1)
        self.refresh_models()

    def refresh_models(self):
        """利用可能なYOLOモデルを更新"""
        self.model_combo.clear()
        from pathlib import Path
        model_files = [
            "yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolov8l.pt", "yolov8x.pt", "yolo11n.pt"
        ]
        for model_file in model_files:
            model_paths = [
                Path.cwd() / model_file,
                Path.cwd() / "yolo" / model_file,
                Path.cwd() / "models" / model_file,
                Path.home() / ".yolo" / "models" / model_file
            ]
            for model_path in model_paths:
                if model_path.exists():
                    self.model_combo.addItem(model_file, str(model_path))
                    break
            else:
                self.model_combo.addItem(f"{model_file} (見つかりません)", model_file)

    def select_image_dir(self):
        """画像フォルダ選択ダイアログ"""
        dir_path = QFileDialog.getExistingDirectory(self, "画像フォルダを選択")
        if dir_path:
            self.image_dir_edit.setText(dir_path)

    def start_prediction(self):
        """推論処理を開始"""
        if self.model_combo.count() == 0:
            QMessageBox.warning(self, "エラー", "モデルが見つかりません")
            return
        model_data = self.model_combo.currentData()
        model_path = model_data
        image_dir = self.image_dir_edit.text()
        conf = self.conf_spin.value() / 100.0
        if not image_dir:
            QMessageBox.warning(self, "エラー", "画像フォルダを選択してください")
            return
        self.predict_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.log_text.clear()
        self.prediction_started.emit(model_path, image_dir, conf)

    def on_prediction_output(self, msg):
        """推論進捗出力"""
        self.log_text.append(msg)

    def on_prediction_finished(self, return_code, result):
        """推論完了時の処理"""
        self.predict_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        if return_code == 0:
            self.log_text.append("推論が完了しました")
        else:
            self.log_text.append(f"推論に失敗しました (コード: {return_code})")
