# YOLOデータセット変換ウィジェット
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout, QPushButton, QLineEdit, QFileDialog, QLabel, QTextEdit, QMessageBox
)
from PyQt6.QtCore import Qt
from ..yolo_dataset_exporter import YoloDatasetExporter
from widgets.components.yolo_dataset_convert_form import YoloDatasetConvertForm
from ..utils.path_manager import PathManager

class YoloDatasetConvertWidget(QWidget):
    """画像リストJSONを選択してYOLOデータセットに変換するウィジェット"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pm = PathManager()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        group = QGroupBox("YOLOデータセット変換")
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(8)
        self.json_edit = QLineEdit()
        self.json_btn = QPushButton("選択...")
        self.json_btn.setFixedWidth(80)
        self.json_btn.clicked.connect(self.select_json)
        json_layout = QHBoxLayout()
        json_layout.addWidget(self.json_edit)
        json_layout.addWidget(self.json_btn)
        json_widget = QWidget()
        json_widget.setLayout(json_layout)
        self.outdir_edit = QLineEdit()
        self.outdir_btn = QPushButton("選択...")
        self.outdir_btn.setFixedWidth(80)
        self.outdir_btn.clicked.connect(self.select_outdir)
        outdir_layout = QHBoxLayout()
        outdir_layout.addWidget(self.outdir_edit)
        outdir_layout.addWidget(self.outdir_btn)
        outdir_widget = QWidget()
        outdir_widget.setLayout(outdir_layout)
        self.convert_btn = QPushButton("データセット変換")
        self.convert_btn.setMinimumHeight(36)
        self.convert_btn.setStyleSheet("font-size: 15px; font-weight: bold;")
        self.convert_btn.clicked.connect(self.convert_dataset)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(120)
        form.addRow("画像リストJSON:", json_widget)
        form.addRow("出力先フォルダ:", outdir_widget)
        group.setLayout(form)
        layout.addWidget(group)
        layout.addWidget(self.convert_btn)
        layout.addWidget(self.log_text)
        layout.addStretch(1)
        # デフォルトパス設定
        default_json = str(self.pm.project_root / "summarygenerator" / "src" / "data")
        default_outdir = str(self.pm.project_root / "summarygenerator" / "datasets" / "yolo_dataset_exported")
        self.json_edit.setPlaceholderText(default_json)
        self.outdir_edit.setPlaceholderText(default_outdir)

    def select_json(self):
        start_dir = str(self.pm.project_root / "summarygenerator" / "src" / "data")
        files, _ = QFileDialog.getOpenFileNames(self, "画像リストJSONを選択", start_dir, "JSON Files (*.json)")
        if files:
            self.json_edit.setText(";".join(files))

    def select_outdir(self):
        start_dir = str(self.pm.project_root / "summarygenerator" / "datasets")
        dir_path = QFileDialog.getExistingDirectory(self, "出力先フォルダを選択", start_dir)
        if dir_path:
            self.outdir_edit.setText(dir_path)

    def convert_dataset(self):
        json_paths = self.form.get_json_paths()
        outdir = self.form.get_outdir()
        if not json_paths:
            QMessageBox.warning(self, "エラー", "画像リストJSONを選択してください")
            return
        self.log_text.clear()
        try:
            exporter = YoloDatasetExporter(json_paths, output_dir=outdir)
            result = exporter.export()
            self.log_text.append("[変換完了] 出力先: {}".format(result["output_dir"]))
            self.log_text.append("ラベル有り画像数: train={}, val={}".format(
                sum(1 for p in result.get('label_file_contents', {}) if 'train' in p),
                sum(1 for p in result.get('label_file_contents', {}) if 'val' in p)))
            if result.get("rejected"):
                self.log_text.append("\n[除外画像]")
                for p, reason in result["rejected"]:
                    self.log_text.append(f"{p}: {reason}")
        except Exception as e:
            import traceback
            self.log_text.append("[エラー] データセット変換に失敗しました\n" + str(e) + "\n" + traceback.format_exc())
