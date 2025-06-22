from PyQt6.QtWidgets import (
    QVBoxLayout, QGroupBox, QFormLayout, QLineEdit, QPushButton, 
    QHBoxLayout, QComboBox, QDoubleSpinBox, QFileDialog, QMessageBox, QWidget
)
from PyQt6.QtCore import Qt
from .common import create_model_combo, create_progress_bar, create_log_text
import os
import json

SETTINGS_PATH = os.path.join(os.path.expanduser("~"), ".yolo_predict_widget_settings.json")

class YoloPredictWidgetUIHelper:
    @staticmethod
    def setup_ui(widget):
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        predict_group = QGroupBox("推論設定")
        predict_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        predict_form = QFormLayout()
        predict_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        predict_form.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        predict_form.setHorizontalSpacing(16)
        predict_form.setVerticalSpacing(8)
        widget.model_combo = create_model_combo(widget)
        widget.model_refresh_btn = QPushButton("更新")
        widget.model_refresh_btn.setFixedWidth(60)
        model_layout = QHBoxLayout()
        model_layout.setContentsMargins(0, 0, 0, 0)
        model_layout.setSpacing(8)
        model_layout.addWidget(widget.model_combo)
        model_layout.addWidget(widget.model_refresh_btn)
        model_widget = QWidget()
        model_widget.setLayout(model_layout)
        widget.image_dir_edit = QLineEdit()
        widget.image_dir_btn = QPushButton("選択...")
        widget.image_dir_btn.setFixedWidth(80)
        image_dir_layout = QHBoxLayout()
        image_dir_layout.setContentsMargins(0, 0, 0, 0)
        image_dir_layout.setSpacing(8)
        image_dir_layout.addWidget(widget.image_dir_edit)
        image_dir_layout.addWidget(widget.image_dir_btn)
        image_dir_widget = QWidget()
        image_dir_widget.setLayout(image_dir_layout)
        widget.conf_spin = QDoubleSpinBox()
        widget.conf_spin.setRange(0.01, 1.0)
        widget.conf_spin.setSingleStep(0.01)
        widget.conf_spin.setDecimals(2)
        widget.conf_spin.setValue(0.10)
        widget.conf_spin.setSuffix("  (conf)")
        widget.conf_spin.setFixedWidth(100)
        predict_form.addRow("モデル:", model_widget)
        predict_form.addRow("画像フォルダ:", image_dir_widget)
        predict_form.addRow("信頼度閾値:", widget.conf_spin)
        predict_group.setLayout(predict_form)
        widget.predict_btn = QPushButton("推論開始")
        widget.predict_btn.setMinimumHeight(40)
        widget.predict_btn.setStyleSheet("font-size: 16px; font-weight: bold;")
        widget.progress_bar = create_progress_bar(widget)
        widget.progress_bar.setFixedHeight(18)
        widget.log_text = create_log_text(widget)
        widget.log_text.setMinimumHeight(120)
        layout.addWidget(predict_group)
        layout.addWidget(widget.predict_btn)
        layout.addWidget(widget.progress_bar)
        layout.addWidget(widget.log_text)
        layout.addStretch(1)

    @staticmethod
    def save_settings(widget):
        current_data = widget.model_combo.currentData()
        model_path = current_data if current_data != "__BROWSE_FOLDER__" else ""
        data = {
            "model_path": model_path,
            "image_dir": widget.image_dir_edit.text(),
            "conf": float(widget.conf_spin.value()),
        }
        try:
            with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[設定保存エラー] {e}")

    @staticmethod
    def restore_settings(widget):
        try:
            if os.path.exists(SETTINGS_PATH):
                with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                model_path = data.get("model_path")
                if model_path:
                    for i in range(widget.model_combo.count()):
                        if widget.model_combo.itemData(i) == model_path:
                            widget.model_combo.setCurrentIndex(i)
                            break
                image_dir = data.get("image_dir")
                if image_dir:
                    widget.image_dir_edit.setText(image_dir)
                conf = data.get("conf")
                if conf is not None:
                    widget.conf_spin.setValue(float(conf))
        except Exception as e:
            print(f"[設定復元エラー] {e}")
