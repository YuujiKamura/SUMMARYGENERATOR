from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import pyqtSignal
from .image_list_widget import ImageListWidget
from src.utils.image_entry import ImageEntry

class ImageListPanel(QWidget):
    """
    画像リスト（サムネイル）部分を分離したパネル
    - 画像リストの表示
    - 画像選択/ダブルクリック/コンテキストメニューのシグナルを外部に橋渡し
    - フォルダコンボの管理は親ウィジェット側で行う想定
    """
    image_selected = pyqtSignal(object)
    image_double_clicked = pyqtSignal(object)
    context_menu_requested = pyqtSignal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        from .image_list_widget import ImageListWidget
        self.image_list_widget = ImageListWidget()
        self.image_list_widget.image_selected.connect(self._on_image_selected)
        self.image_list_widget.image_double_clicked.connect(self._on_image_double_clicked)
        self._context_menu_handler = None
        self.image_list_widget.context_menu_requested.connect(self._on_context_menu)
        layout = QVBoxLayout(self)
        layout.addWidget(self.image_list_widget)

    def update_image_list(self, img_entries):
        self.image_list_widget.update_image_list(img_entries)

    def _on_image_selected(self, entry):
        self.image_selected.emit(entry)

    def _on_image_double_clicked(self, entry):
        self.image_double_clicked.emit(entry)

    def _on_context_menu(self, items, pos):
        if self._context_menu_handler:
            self._context_menu_handler(self, items, pos)
        else:
            self.context_menu_requested.emit(items, pos)

    @property
    def _img_paths(self):
        return getattr(self.image_list_widget, '_img_paths', [])

    def currentItem(self):
        return self.image_list_widget.currentItem()

    def refresh_current_items(self):
        self.image_list_widget.refresh_current_items()

    def set_context_menu_handler(self, handler):
        """
        外部からcontext menu handlerを差し込む
        handler(self, items, pos) の形で呼ばれる
        """
        self._context_menu_handler = handler
