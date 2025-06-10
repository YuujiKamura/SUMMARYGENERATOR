import pytest
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QPixmap, QColor
from src.image_preview_dialog import ImagePreviewDialog
from src.utils.bbox_utils import BoundingBox

@pytest.fixture
def dialog(qtbot):
    # ダミー画像を使う
    dlg = ImagePreviewDialog("")
    qtbot.addWidget(dlg)
    # 100x100のダミー画像
    pixmap = QPixmap(100, 100)
    pixmap.fill(QColor(255, 255, 255))
    dlg.image_widget._pixmap = pixmap
    dlg.image_widget._orig_size = (100, 100)
    dlg.image_widget.setFixedSize(100, 100)
    dlg.image_widget._zoom_scale = 1.0
    dlg.image_widget._offset_x = 0
    dlg.image_widget._offset_y = 0
    dlg.show()
    qtbot.waitExposed(dlg)
    return dlg

def test_ctrl_click_multi_select(qtbot, dialog):
    b1 = BoundingBox(0, "A", 1.0, [10, 10, 50, 50], "role1")
    b2 = BoundingBox(1, "B", 1.0, [60, 60, 90, 90], "role2")
    dialog.image_widget.set_bboxes([b1, b2])
    dialog.image_widget.set_roles([
        {"label": "role1", "display": "役割1"},
        {"label": "role2", "display": "役割2"},
    ])
    dialog.image_widget.update()
    qtbot.wait(100)

    def center(xyxy):
        x1, y1, x2, y2 = xyxy
        return QPoint(int((x1 + x2) / 2), int((y1 + y2) / 2))

    pt1 = center(b1.xyxy)
    pt2 = center(b2.xyxy)

    qtbot.mouseClick(dialog.image_widget, Qt.MouseButton.LeftButton, pos=pt1)
    assert dialog.image_widget.selected_indices == [0]

    qtbot.mouseClick(dialog.image_widget, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier, pos=pt2)
    assert set(dialog.image_widget.selected_indices) == {0, 1} 