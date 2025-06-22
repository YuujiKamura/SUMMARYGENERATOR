# YOLO推論ウィジェット（PhotoCategorizerからコピー）
#!/usr/bin/env python3
# flake8: noqa
"""
YOLO推論ウィジェット
"""
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QFormLayout, QLineEdit, QPushButton, 
    QHBoxLayout, QComboBox, QDoubleSpinBox, QFileDialog, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, Qt, QThread, pyqtSlot
from .common import create_model_combo, create_progress_bar, create_log_text
from src.utils.path_manager import PathManager # PathManager クラスをインポート
from .detect_result_widget import DetectResultWidget
from src.engines.yolo_engine import YoloDetectionEngine
from src.services.cache_manager import CacheManager
from .yolo_predict_widget_uihelper import YoloPredictWidgetUIHelper
import os
import csv
import json
SETTINGS_PATH = os.path.join(os.path.expanduser("~"), ".yolo_predict_widget_settings.json")

class YoloPredictThread(QThread):
    output = pyqtSignal(str)
    finished = pyqtSignal(int, str)
    def __init__(self, model_path, image_dir, conf, parent=None, cache_manager=None):
        super().__init__(parent)
        self.model_path = model_path
        self.image_dir = image_dir
        self.conf = conf
        self.cache_manager = cache_manager or CacheManager()

    def _apply_dataset_names(self, model):
        """model.model.names が全て 'unknown' の場合、直近の dataset.yaml から名前リストを適用する"""
        try:
            # 既存 names が unknown ばかりなら置き換え対象とみなす
            current_names = getattr(model.model, "names", {})
            if current_names and all("unknown" in str(n).lower() for n in current_names.values()):
                from pathlib import Path
                import yaml  # PyYAML

                model_path = Path(self.model_path).resolve()
                # 6階層以内で dataset.yaml を探す
                dataset_yaml = None
                for parent in list(model_path.parents)[:6]:
                    cand = parent / "dataset.yaml"
                    if cand.exists():
                        dataset_yaml = cand
                        break
                if dataset_yaml:
                    with open(dataset_yaml, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                    names_list = data.get("names")
                    if isinstance(names_list, list):
                        names_dict = {i: n for i, n in enumerate(names_list)}
                        model.model.names = names_dict
                        self.output.emit(f"dataset.yaml からクラス名を適用: {dataset_yaml}")
        except Exception as e:
            self.output.emit(f"[names適用エラー] {e}")

    def run(self):
        try:
            engine = YoloDetectionEngine(model=self.model_path)
            cache_ns = getattr(engine, 'cache_ns', 'yolo_bboxes')
            import glob
            import tempfile, json, os
            image_files = glob.glob(os.path.join(self.image_dir, '*'))
            parsed_results = []
            for img_path in image_files:
                # キャッシュ確認
                cached = self.cache_manager.load_engine_cache(img_path, cache_ns)
                if cached is not None:
                    self.output.emit(f"[キャッシュHIT] {img_path}")
                    result = cached
                else:
                    self.output.emit(f"[推論] {img_path}")
                    result = engine.detect(img_path)
                    self.cache_manager.save_engine_cache(img_path, cache_ns, result)
                dets = []
                for bbox in result.get('bboxes', []):
                    dets.append({
                        'bbox': bbox.get('bbox', bbox.get('xyxy', [])),
                        'class_name': bbox.get('class_name', bbox.get('class', '')),
                        'confidence': bbox.get('confidence', bbox.get('conf', 0.0)),
                    })
                parsed_results.append({'image_path': img_path, 'detections': dets})
            with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', suffix='.json') as tf:
                json.dump(parsed_results, tf, ensure_ascii=False, indent=2)
                temp_json_path = tf.name
            self.output.emit(f"推論結果JSON: {temp_json_path}")
            self.finished.emit(0, temp_json_path)
        except Exception as e:
            self.output.emit(f"推論エラー: {e}")
            self.finished.emit(1, str(e))

class YoloPredictWidget(QWidget):
    """YOLO推論用のウィジェット。モデル・画像フォルダ・信頼度閾値を指定し、推論処理を開始できる。"""
    prediction_started = pyqtSignal(str, str, float)

    def __init__(self, settings_manager=None, parent=None):
        super().__init__(parent)
        self.settings = settings_manager
        self.path_manager = PathManager()
        YoloPredictWidgetUIHelper.setup_ui(self)
        self.model_refresh_btn.clicked.connect(self.refresh_models)
        self.image_dir_btn.clicked.connect(self.select_image_dir)
        self.predict_btn.clicked.connect(self.start_prediction)
        self.refresh_models()
        YoloPredictWidgetUIHelper.restore_settings(self)

    def save_settings(self):
        YoloPredictWidgetUIHelper.save_settings(self)

    def restore_settings(self):
        YoloPredictWidgetUIHelper.restore_settings(self)

    def closeEvent(self, event):
        self.save_settings()
        super().closeEvent(event)

    def refresh_models(self):
        self.model_combo.clear()
        from pathlib import Path
        import os
        model_files = [
            "yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolov8l.pt", "yolov8x.pt", "yolo11n.pt"
        ]
        seen = set()
        for model_file in model_files:
            model_paths = [
                Path.cwd() / model_file,
                self.path_manager.src_dir / "yolo" / model_file,
                self.path_manager.src_dir / "datasets" / model_file,
                Path.home() / ".yolo" / "models" / model_file
            ]
            for model_path in model_paths:
                if model_path.exists() and str(model_path) not in seen:
                    self.model_combo.addItem(f"{model_file} (Official/Common)", str(model_path))
                    seen.add(str(model_path))
                    break
        base_dirs = [
            self.path_manager.project_root,
            self.path_manager.src_dir / "yolo",
            self.path_manager.src_dir / "datasets",
        ]
        home_yolo_dir = Path.home() / ".yolo" / "models"
        if home_yolo_dir.exists() and home_yolo_dir not in base_dirs:
            base_dirs.append(home_yolo_dir)
        for base in base_dirs:
            if base.exists():
                for pt in base.rglob("*.pt"):
                    if str(pt) not in seen:
                        label = ""
                        try:
                            relative_path = pt.relative_to(self.path_manager.project_root)
                            if "logs" in relative_path.parts and "weights" in relative_path.parts:
                                if pt.name == "best.pt":
                                    label = f"🏆 {relative_path} (Best Trained)"
                                elif pt.name == "last.pt":
                                    label = f"📈 {relative_path} (Last Trained)"
                                else:
                                    label = f"🎯 {relative_path} (Trained)"
                            else:
                                label = f"{relative_path} (Project)"
                        except ValueError:
                            try:
                                relative_path = pt.relative_to(self.path_manager.src_dir)
                                label = f"{relative_path} (Src)"
                            except ValueError:
                                label = f"{pt.name} ({pt.parent.name})"
                        self.model_combo.addItem(label, str(pt))
                        seen.add(str(pt))
        if self.model_combo.count() == 0:
            self.model_combo.addItem("(モデルが見つかりません)", "")
        self.model_combo.addItem("📁 フォルダから選ぶ...", "__BROWSE_FOLDER__")
        self.restore_settings()

    def select_image_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "画像フォルダを選択")
        if dir_path:
            self.image_dir_edit.setText(dir_path)
        self.save_settings()

    def start_prediction(self):
        if self.model_combo.count() == 0:
            QMessageBox.warning(self, "エラー", "モデルが見つかりません")
            return
        model_data = self.model_combo.currentData()
        if model_data == "__BROWSE_FOLDER__":
            QMessageBox.warning(self, "エラー", "有効なモデルを選択してください")
            return
        if not model_data or model_data == "":
            QMessageBox.warning(self, "エラー", "有効なモデルを選択してください")
            return
        model_path = model_data
        image_dir = self.image_dir_edit.text()
        conf = float(self.conf_spin.value())
        if not image_dir:
            QMessageBox.warning(self, "エラー", "画像フォルダを選択してください")
            return
        self.predict_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.log_text.clear()
        self._thread = YoloPredictThread(model_path, image_dir, conf, cache_manager=CacheManager())
        self._thread.output.connect(self.on_prediction_output)
        self._thread.finished.connect(self.on_prediction_finished)
        self._thread.start()

    @pyqtSlot(str)
    def on_prediction_output(self, msg):
        self.log_text.append(msg)

    @pyqtSlot(int, str)
    def on_prediction_finished(self, return_code, result):
        import os
        from src.utils.path_manager import path_manager
        self.predict_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        if return_code == 0:
            self.log_text.append(f"推論が完了しました\n結果: {result}")
            if result.endswith('.json') and os.path.exists(result):
                with open(result, 'r', encoding='utf-8') as f:
                    parsed_results = json.load(f)
                image_paths = []
                bbox_dict = {}
                for entry in parsed_results:
                    img_path = entry.get('image_path')
                    dets = entry.get('detections', [])
                    if img_path:
                        image_paths.append(img_path)
                        bbox_dict[img_path] = dets
                self.result_widget = DetectResultWidget()
                self.result_widget.set_images(image_paths, bbox_dict)
                from pathlib import Path
                image_list_json = str(path_manager.last_images)
                Path(image_list_json).parent.mkdir(parents=True, exist_ok=True)
                try:
                    with open(image_list_json, "w", encoding="utf-8") as f:
                        json.dump(image_paths, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    self.log_text.append(f"[画像リスト保存エラー] {e}")
        else:
            self.log_text.append(f"推論エラー: {result}")
