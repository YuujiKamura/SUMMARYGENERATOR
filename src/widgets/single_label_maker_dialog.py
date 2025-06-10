from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QLabel, QMessageBox, QTextEdit, QGraphicsView, QGraphicsPixmapItem, QMenu
from widgets.annotation_view_widget import AnnotationViewWidget
from utils.last_opened_path import save_last_path, load_last_path
from utils.image_cache_utils import save_image_cache, load_image_cache
from widgets.role_editor_dialog import RoleEditorDialog
from utils.roles_utils import group_roles_by_category
import os
import json
from widgets.image_display_widget import EditableImageDisplayWidget
from utils.bbox_utils import BoundingBox
from PyQt6.QtGui import QPixmap, QTransform, QCursor
from PyQt6.QtCore import QRectF, pyqtSignal
from components.json_bbox_viewer_dialog import JsonBboxViewerDialog

class SingleLabelMakerDialog(QDialog):
    # ... (src/single_label_maker_dialog.pyの本体をここに移植)
