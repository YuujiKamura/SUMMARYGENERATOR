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
            from ultralytics import YOLO
            import os
            self.output.emit(f"モデル: {self.model_path}\n画像フォルダ: {self.image_dir}\n信頼度閾値: {self.conf}")
            model = YOLO(self.model_path)
            # クラス名対応を補正
            self._apply_dataset_names(model)
            results = model.predict(source=self.image_dir, conf=self.conf, save=False, show=False)
            # save=FalseなのでCSVやruns/detect/predictは生成されない
            # ここでresultsから直接検出結果をパースしてemit
            parsed_results = []
            for r in results:
                img_path = r.path if hasattr(r, 'path') else None
                names = r.names if hasattr(r, 'names') else {}
                self.output.emit(f"[DEBUG] {img_path}: det={len(r.boxes)}")
                dets = []
                if hasattr(r, 'boxes') and r.boxes is not None:
                    for box in r.boxes:
                        cls_id = int(box.cls[0]) if hasattr(box, 'cls') else -1
                        conf = float(box.conf[0]) if hasattr(box, 'conf') else 0.0
                        xyxy = box.xyxy[0].tolist() if hasattr(box, 'xyxy') else [0,0,0,0]
                        class_name = names.get(cls_id, str(cls_id)) if isinstance(names, dict) else str(cls_id)
                        dets.append({'bbox': xyxy, 'class_name': class_name, 'confidence': conf})
                parsed_results.append({'image_path': img_path, 'detections': dets})
            # 検出結果を一時ファイルに保存してパスをemit（既存on_prediction_finishedの流れを崩さないため）
            import tempfile, json
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
        """初期化"""
        super().__init__(parent)
        self.settings = settings_manager
        self.path_manager = PathManager() # PathManagerのインスタンスを生成・保持
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
        self.model_combo.currentTextChanged.connect(self._on_model_selection_changed)
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
        self.conf_spin = QDoubleSpinBox()
        self.conf_spin.setRange(0.01, 1.0)
        self.conf_spin.setSingleStep(0.01)
        self.conf_spin.setDecimals(2)
        self.conf_spin.setValue(0.10)
        self.conf_spin.setSuffix("  (conf)")
        self.conf_spin.setFixedWidth(100)
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
        current_data = self.model_combo.currentData()
        # 特別なエントリーは保存しない
        model_path = current_data if current_data != "__BROWSE_FOLDER__" else ""
        
        data = {
            "model_path": model_path,
            "image_dir": self.image_dir_edit.text(),
            "conf": float(self.conf_spin.value()),
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
                if conf is not None:
                    self.conf_spin.setValue(float(conf))
        except Exception as e:
            print(f"[設定復元エラー] {e}")

    def closeEvent(self, event):
        self.save_settings()
        super().closeEvent(event)

    def refresh_models(self):
        """src/yolo, src/datasets配下の.ptモデルを再帰的に探索し、モデルリストを更新"""
        self.model_combo.clear()
        from pathlib import Path
        import os
        # 公式プリセット
        model_files = [
            "yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolov8l.pt", "yolov8x.pt", "yolo11n.pt"
        ]
        seen = set()
        # 公式モデル
        for model_file in model_files:
            model_paths = [
                Path.cwd() / model_file,
                self.path_manager.src_dir / "yolo" / model_file, # path_manager を使用
                self.path_manager.src_dir / "datasets" / model_file, # path_manager を使用
                Path.home() / ".yolo" / "models" / model_file
            ]
            for model_path in model_paths:
                if model_path.exists() and str(model_path) not in seen:
                    self.model_combo.addItem(f"{model_file} (Official/Common)", str(model_path))
                    seen.add(str(model_path))
                    break
          # path_manager を使用して検索パスを構築
        base_dirs = [
            self.path_manager.project_root,  # summarygenerator フォルダ
            self.path_manager.src_dir / "yolo",
            self.path_manager.src_dir / "datasets",
            self.path_manager.project_root / "logs"  # トレーニング結果のlogsディレクトリを追加
        ]
        # ホームディレクトリの .yolo/models も追加
        home_yolo_dir = Path.home() / ".yolo" / "models"
        if home_yolo_dir.exists() and home_yolo_dir not in base_dirs: # 重複を避ける
            base_dirs.append(home_yolo_dir)

        for base in base_dirs:
            if base.exists():
                for pt in base.rglob("*.pt"):
                    if str(pt) not in seen:
                        label = ""
                        try:
                            # project_root からの相対パスを試みる
                            relative_path = pt.relative_to(self.path_manager.project_root)
                            
                            # トレーニング済みモデルの特別識別
                            if "logs" in relative_path.parts and "weights" in relative_path.parts:
                                # logs/training_run_*/exp/weights/best.pt のようなパス
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
                                # src_dir からの相対パスを試みる
                                relative_path = pt.relative_to(self.path_manager.src_dir)
                                label = f"{relative_path} (Src)"
                            except ValueError:
                                # その他の場合はファイル名と親ディレクトリ名
                                label = f"{pt.name} ({pt.parent.name})"
                        
                        self.model_combo.addItem(label, str(pt))
                        seen.add(str(pt))
        if self.model_combo.count() == 0:
            self.model_combo.addItem("(モデルが見つかりません)", "")
        
        # 「フォルダから選ぶ」エントリーを追加
        self.model_combo.addItem("📁 フォルダから選ぶ...", "__BROWSE_FOLDER__")
        
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
        
        # 特別なエントリーの場合はエラー表示
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
        import os
        from src.utils.path_manager import path_manager
        self.predict_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        if return_code == 0:
            self.log_text.append(f"推論が完了しました\n結果: {result}")
            # --- 推論結果JSONをパースしてDetectResultWidgetで可視化 ---
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
                # DetectResultWidgetを表示
                self.result_widget = DetectResultWidget()
                self.result_widget.set_images(image_paths, bbox_dict)
                # --- パスマネージャーで保存パスを取得 ---
                from pathlib import Path
                image_list_json = str(path_manager.last_images)
                Path(image_list_json).parent.mkdir(parents=True, exist_ok=True)
                try:
                    with open(image_list_json, "w", encoding="utf-8") as f:
                        json.dump(image_paths, f, ensure_ascii=False, indent=2)
                    print(f"[画像リスト保存] {image_list_json} ({len(image_paths)}件)")
                    path_manager.current_image_list_json = image_list_json
                except Exception as e:
                    print(f"[画像リスト保存エラー] {e}")
                self.result_widget.show()
                # --- 検出結果もlast_detect_results.jsonに保存 ---
                detect_result_json = os.path.join(os.path.dirname(__file__), '..', 'data', 'last_detect_results.json')
                from pathlib import Path
                Path(os.path.dirname(detect_result_json)).mkdir(parents=True, exist_ok=True)
                try:
                    with open(detect_result_json, "w", encoding="utf-8") as f:
                        json.dump({'image_paths': image_paths, 'bbox_dict': bbox_dict}, f, ensure_ascii=False, indent=2)
                    print(f"[検出結果保存] {detect_result_json} 画像: {len(image_paths)}件 bbox_dict: {len(bbox_dict)}件")
                except Exception as e:
                    print(f"[検出結果保存エラー] {e}")
            else:
                self.log_text.append(f"[警告] 推論結果JSONが見つかりません: {result}")
        else:
            self.log_text.append(f"推論に失敗しました (コード: {return_code})\n{result}")
        self.save_settings()

    def _on_model_selection_changed(self, text):
        """モデル選択が変更された時の処理"""
        current_data = self.model_combo.currentData()
        if current_data == "__BROWSE_FOLDER__":
            self._select_model_file()
    
    def _select_model_file(self):
        """モデルファイル選択ダイアログを表示"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "YOLOモデルファイルを選択", 
            "", 
            "YOLO Models (*.pt);;All Files (*)"
        )
        if file_path:
            # 新しいエントリーとして追加
            from pathlib import Path
            model_path = Path(file_path)
            label = f"{model_path.name} (選択済み)"
            
            # 既に同じパスが存在するかチェック
            for i in range(self.model_combo.count()):
                if self.model_combo.itemData(i) == file_path:
                    self.model_combo.setCurrentIndex(i)
                    return
            
            # 「フォルダから選ぶ」エントリーの前に挿入
            browse_index = self.model_combo.count() - 1  # 最後のエントリー
            self.model_combo.insertItem(browse_index, label, file_path)
            self.model_combo.setCurrentIndex(browse_index)
        else:
            # キャンセルされた場合は元の選択に戻す
            if self.model_combo.count() > 1:
                self.model_combo.setCurrentIndex(0)
