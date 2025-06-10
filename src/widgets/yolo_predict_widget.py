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
from PyQt6.QtCore import pyqtSignal, Qt, QThread, pyqtSlot
from .common import create_model_combo, create_progress_bar, create_log_text
from src.utils.path_manager import path_manager
from .detect_result_widget import DetectResultWidget
import os
import csv
import json
SETTINGS_PATH = os.path.join(os.path.expanduser("~"), ".yolo_predict_widget_settings.json")

class YoloPredictThread(QThread):
    output = pyqtSignal(str)
    finished = pyqtSignal(int, str)
    def __init__(self, model_path, image_dir, conf, parent=None):
        super().__init__(parent)
        self.model_path = model_path
        self.image_dir = image_dir
        self.conf = conf
    def run(self):
        try:
            from ultralytics import YOLO
            import os
            self.output.emit(f"モデル: {self.model_path}\n画像フォルダ: {self.image_dir}\n信頼度閾値: {self.conf}")
            model = YOLO(self.model_path)
            results = model.predict(source=self.image_dir, conf=self.conf, save=True, show=False)
            # 結果保存先ディレクトリ取得（resultsはリスト）
            if results and hasattr(results[0], 'save_dir'):
                save_dir = str(results[0].save_dir)
            else:
                save_dir = 'runs/detect/predict'
            self.output.emit(f"推論結果保存先: {save_dir}")
            # 検出結果をCSVで保存
            csv_path = os.path.join(save_dir, 'predict_results.csv')
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['image', 'class_id', 'class_name', 'confidence', 'xmin', 'ymin', 'xmax', 'ymax'])
                for r in results:
                    img_name = os.path.basename(r.path) if hasattr(r, 'path') else ''
                    names = r.names if hasattr(r, 'names') else {}
                    if hasattr(r, 'boxes') and r.boxes is not None:
                        for box in r.boxes:
                            cls_id = int(box.cls[0]) if hasattr(box, 'cls') else -1
                            conf = float(box.conf[0]) if hasattr(box, 'conf') else 0.0
                            xyxy = box.xyxy[0].tolist() if hasattr(box, 'xyxy') else [0,0,0,0]
                            class_name = names.get(cls_id, str(cls_id)) if isinstance(names, dict) else str(cls_id)
                            writer.writerow([img_name, cls_id, class_name, conf, *xyxy])
            self.output.emit(f"検出結果CSV: {csv_path}")
            self.finished.emit(0, save_dir)
        except Exception as e:
            self.output.emit(f"推論エラー: {e}")
            self.finished.emit(1, str(e))

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
        self.restore_settings()

    def save_settings(self):
        """現在のモデル・画像フォルダを保存"""
        data = {
            "model_path": self.model_combo.currentData(),
            "image_dir": self.image_dir_edit.text(),
            "conf": self.conf_spin.value(),
        }
        try:
            with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[設定保存エラー] {e}")

    def restore_settings(self):
        """前回保存したモデル・画像フォルダを復元"""
        try:
            if os.path.exists(SETTINGS_PATH):
                with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # モデルパス復元
                model_path = data.get("model_path")
                if model_path:
                    for i in range(self.model_combo.count()):
                        if self.model_combo.itemData(i) == model_path:
                            self.model_combo.setCurrentIndex(i)
                            break
                # 画像フォルダ復元
                image_dir = data.get("image_dir")
                if image_dir:
                    self.image_dir_edit.setText(image_dir)
                # 信頼度復元
                conf = data.get("conf")
                if conf:
                    self.conf_spin.setValue(conf)
        except Exception as e:
            print(f"[設定復元エラー] {e}")

    def closeEvent(self, event):
        self.save_settings()
        super().closeEvent(event)

    def refresh_models(self):
        """利用可能なYOLOモデルを更新（パスマネージャー経由でsrc/datasets配下の自作モデルも含める）"""
        self.model_combo.clear()
        from pathlib import Path
        # 公式プリセット
        model_files = [
            "yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolov8l.pt", "yolov8x.pt", "yolo11n.pt"
        ]
        # 公式プリセットのパス候補
        for model_file in model_files:
            model_paths = [
                Path.cwd() / model_file,
                path_manager.yolo_model_dir / model_file,
                path_manager.models_dir / model_file,
                Path.home() / ".yolo" / "models" / model_file
            ]
            for model_path in model_paths:
                if model_path.exists():
                    self.model_combo.addItem(f"{model_file} (公式/共通)", str(model_path))
                    break
        # src/datasets配下の自作モデル（best.pt, last.pt）を再帰的に探索
        datasets_dir = path_manager.project_root / "datasets"
        for dataset_dir in datasets_dir.glob("yolo_dataset_all_*/train_run/exp/weights"):
            for pt_file in dataset_dir.glob("*.pt"):
                label = f"{pt_file.parent.parent.parent.parent.name}/{pt_file.name} (自作)"
                self.model_combo.addItem(label, str(pt_file))
        # モデルリスト更新後に復元も再実行
        self.restore_settings()

    def select_image_dir(self):
        """画像フォルダ選択ダイアログ"""
        dir_path = QFileDialog.getExistingDirectory(self, "画像フォルダを選択")
        if dir_path:
            self.image_dir_edit.setText(dir_path)
        self.save_settings()

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
        # self.prediction_started.emit(model_path, image_dir, conf)  # ← 旧シグナルは使わない
        # サブスレッドで推論実行
        self._thread = YoloPredictThread(model_path, image_dir, conf)
        self._thread.output.connect(self.on_prediction_output)
        self._thread.finished.connect(self.on_prediction_finished)
        self._thread.start()

    @pyqtSlot(str)
    def on_prediction_output(self, msg):
        self.log_text.append(msg)

    @pyqtSlot(int, str)
    def on_prediction_finished(self, return_code, result):
        self.predict_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        if return_code == 0:
            self.log_text.append(f"推論が完了しました\n結果フォルダ: {result}")
            # --- 推論結果CSVをパースしてDetectResultWidgetで可視化 ---
            csv_path = os.path.join(result, 'predict_results.csv')
            if os.path.exists(csv_path):
                image_paths = []
                bbox_dict = {}
                with open(csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        img = row['image']
                        img_path = os.path.join(result, 'labels', '..', img) if not os.path.isabs(img) else img
                        bbox = [float(row['xmin']), float(row['ymin']), float(row['xmax']), float(row['ymax'])]
                        det = {
                            'bbox': bbox,
                            'class_name': row['class_name'],
                            'confidence': float(row['confidence'])
                        }
                        if img_path not in bbox_dict:
                            bbox_dict[img_path] = []
                            image_paths.append(img_path)
                        bbox_dict[img_path].append(det)
                # DetectResultWidgetを表示
                self.result_widget = DetectResultWidget()
                self.result_widget.set_images(image_paths, bbox_dict)
                self.result_widget.show()
            else:
                self.log_text.append(f"[警告] predict_results.csvが見つかりません: {csv_path}")
        else:
            self.log_text.append(f"推論に失敗しました (コード: {return_code})\n{result}")
        self.save_settings()
