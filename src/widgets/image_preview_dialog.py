import sys
import os
import pickle
import json
from pathlib import Path
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QComboBox, QApplication, QMessageBox, QMenu, QListWidget, QWidgetAction, QCheckBox, QHBoxLayout, QTextEdit, QStatusBar
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QCursor
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from utils.bbox_utils import is_point_in_bbox_scaled, BoundingBox
import hashlib
from widgets.role_editor_dialog import RoleEditorDialog
import importlib
from utils.image_cache_utils import save_image_cache, load_image_cache, get_image_cache_path
from widgets.image_display_widget import ImageDisplayWidget
from widgets.single_label_maker_dialog import SingleLabelMakerDialog
from utils.last_opened_path import save_last_path, load_last_path
from components.role_tree_selector import RoleTreeSelector
from utils.path_manager import path_manager
from components.json_bbox_viewer_dialog import JsonBboxViewerDialog
from utils.location_utils import LocationInputDialog, load_location_history, save_location_history

# --- Copied from src/image_preview_dialog.py ---
# widgets/配下に移動したため、importは from summarygenerator.widgets. で参照
