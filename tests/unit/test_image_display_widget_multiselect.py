import pytest
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QPixmap, QColor
from src.image_display_widget import ImageDisplayWidget
from src.utils.bbox_utils import BoundingBox

@pytest.fixture
def widget(qtbot):
    w = ImageDisplayWidget()
    qtbot.addWidget(w)
    pixmap = QPixmap(100, 100)
    pixmap.fill(QColor(255, 255, 255))
    w._pixmap = pixmap
    w._orig_size = (100, 100)
    w.setFixedSize(100, 100)
    w._zoom_scale = 1.0
    w._offset_x = 0
    w._offset_y = 0
    w.show()
    qtbot.waitExposed(w)
    return w

def test_ctrl_click_multi_select(qtbot, widget):
    b1 = BoundingBox(0, "A", 1.0, [10, 10, 50, 50], "role1")
    b2 = BoundingBox(1, "B", 1.0, [60, 60, 90, 90], "role2")
    widget.set_bboxes([b1, b2])
    widget.set_roles([
        {"label": "role1", "display": "役割1"},
        {"label": "role2", "display": "役割2"},
    ])
    widget.update()
    qtbot.wait(100)

    def center(xyxy):
        x1, y1, x2, y2 = xyxy
        return QPoint(int((x1 + x2) / 2), int((y1 + y2) / 2))

    pt1 = center(b1.xyxy)
    pt2 = center(b2.xyxy)

    qtbot.mouseClick(widget, Qt.MouseButton.LeftButton, pos=pt1)
    assert widget.selected_indices == [0]

    qtbot.mouseClick(widget, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier, pos=pt2)
    assert set(widget.selected_indices) == {0, 1} 