from PyQt6.QtWidgets import QWidget, QMenu
from PyQt6.QtCore import Qt
import json
from pathlib import Path
from src.utils.path_manager import path_manager
from src.utils.chain_record import ChainRecord
import os

class IncorrectMarkerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.incorrect_entries = []
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, pos):
        menu = QMenu(self)
        mark_action = menu.addAction("不正解としてマーク")
        action = menu.exec(self.mapToGlobal(pos))
        
        if action == mark_action:
            self.mark_current_as_incorrect()

    def mark_current_as_incorrect(self):
        if not hasattr(self.parent(), 'image_widget'):
            return
            
        current_image = self.parent().image_widget.current_image
        if not current_image or not hasattr(self.parent(), 'bbox_dict'):
            return
            
        bbox_dict = self.parent().bbox_dict
        if current_image not in bbox_dict:
            return

        record = ChainRecord(
            image_path=current_image,
            bbox=bbox_dict[current_image],
            remarks="incorrect_detection"
        )
        self.incorrect_entries.append(record)
        self.save_incorrect_entries()

    def save_incorrect_entries(self):
        if not self.incorrect_entries:
            return
        
        output_path = os.path.join(path_manager.get_retrain_data_dir(), "incorrect_entries.json")
        Path(os.path.dirname(output_path)).mkdir(parents=True, exist_ok=True)
        
        data = [record.to_dict() for record in self.incorrect_entries]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2) 