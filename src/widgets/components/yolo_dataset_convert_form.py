from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QPushButton, QLineEdit, QFileDialog, QTextEdit, QMessageBox
)
from PyQt6.QtCore import Qt

class YoloDatasetConvertForm(QWidget):
    """画像リストJSONと出力先を選択するフォーム部品"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
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
        form.addRow("画像リストJSON:", json_widget)
        form.addRow("出力先フォルダ:", outdir_widget)
        layout.addLayout(form)
        layout.addStretch(1)

    def select_json(self):
        files, _ = QFileDialog.getOpenFileNames(self, "画像リストJSONを選択", "", "JSON Files (*.json)")
        if files:
            self.json_edit.setText(";".join(files))

    def select_outdir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "出力先フォルダを選択")
        if dir_path:
            self.outdir_edit.setText(dir_path)

    def get_json_paths(self):
        return [p for p in self.json_edit.text().split(";") if p.strip()]

    def get_outdir(self):
        return self.outdir_edit.text().strip() or None 