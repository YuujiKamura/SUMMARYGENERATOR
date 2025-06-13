from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox, QLabel, QStatusBar
from PyQt6.QtGui import QIcon
from src.ui.components.ui_action_loader import load_actions_yaml
from src.widgets.model_selector_widget import ModelSelectorWidget
from src.widgets.image_display_widget import ImageDisplayWidget

def build_image_preview_ui(self):
    vbox = QVBoxLayout(self)
    # モデル選択
    self.model_selector = ModelSelectorWidget(self)
    vbox.addWidget(self.model_selector)
    self.selected_model_path = self.model_selector.get_selected_model_path()
    # 画像表示
    self.image_widget = ImageDisplayWidget(self)
    self.image_widget.draw_global_selection_frame = False
    vbox.addWidget(self.image_widget)
    # 下部ボタン
    bottom_vbox = QVBoxLayout()
    btn_hbox = QHBoxLayout()
    for cfg in load_actions_yaml():
        btn = QPushButton(cfg["label"])
        if cfg.get("icon"):
            btn.setIcon(QIcon(cfg["icon"]))
        btn.clicked.connect(getattr(self, cfg["slot"]))
        if cfg.get("shortcut"):
            btn.setShortcut(cfg["shortcut"])
        btn_hbox.addWidget(btn)
        # 主要ボタンは属性として保持
        if cfg["slot"] == "run_yolo_detection":
            self.detect_btn = btn
        elif cfg["slot"] == "open_single_label_maker":
            self.single_label_btn = btn
        elif cfg["slot"] == "show_current_json":
            self.show_json_btn = btn
        elif cfg["slot"] == "assign_location":
            self.assign_location_btn = btn
        elif cfg["slot"] == "accept":
            self.accept_btn = btn
    bottom_vbox.addLayout(btn_hbox)
    self.merge_checkbox = QCheckBox("ロール割当をマージ")
    self.merge_checkbox.setChecked(True)
    bottom_vbox.addWidget(self.merge_checkbox)
    vbox.addLayout(bottom_vbox)
    # ステータスバー
    self.status_bar = QStatusBar(self)
    self.location_label = QLabel()
    self.location_label.setStyleSheet("font-weight: bold; color: #1a237e; padding: 2px 0;")
    self.status_bar.addWidget(self.location_label, 1)
    self.status_label = QLabel("")
    self.status_bar.addPermanentWidget(self.status_label, 1)
    vbox.addWidget(self.status_bar)
    self.setMinimumSize(400, 300)
    vbox.setContentsMargins(4, 4, 4, 4)
    vbox.setSpacing(4)
    self.setLayout(vbox)
