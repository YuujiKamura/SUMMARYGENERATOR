from PyQt6.QtWidgets import QWidget, QLabel, QMenu, QListWidget, QWidgetAction, QTreeWidget, QTreeWidgetItem
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QMouseEvent, QWheelEvent
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QRectF
from src.utils.bbox_utils import BoundingBox
from src.utils.image_cache_utils import save_image_cache, load_image_cache
from typing import List

class ImageDisplayWidget(QWidget):
    box_clicked = pyqtSignal(list)  # List[int]
    box_right_clicked = pyqtSignal(list)
    box_double_clicked = pyqtSignal(list)  # 追加: ダブルクリック
    role_edit_requested = pyqtSignal()  # 親Dialogにロール編集を依頼するsignal
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None
        self._orig_size = (0, 0)
        self.bboxes = []
        self.selected_indices = []
        self._zoom_levels = [0.5, 1.0, 1.5]
        self._zoom_idx = 0
        self._zoom_scale = self._zoom_levels[self._zoom_idx]
        self._offset_x = 0
        self._offset_y = 0
        self.roles = []
        self.setMinimumSize(200, 150)
        self.draw_global_selection_frame = True  # 青枠描画制御フラグ（デフォルトTrue）
        self._drawing = False  # 追加: サブクラスとの整合性のため

    def set_image(self, image_path):
        print(f"[DEBUG IDW] set_image called with path: {image_path}")
        
        from pathlib import Path
        import os
        
        # 複数の方法で画像読み込みを試す
        self._pixmap = QPixmap()
        
        load_methods = [
            # 方法1: 直接パスを使用
            lambda: QPixmap(image_path),
            # 方法2: pathlibを使用
            lambda: QPixmap(str(Path(image_path))),
            # 方法3: os.fsdecodeを使用
            lambda: QPixmap(os.fsdecode(image_path)),
            # 方法4: フルパスに変換
            lambda: QPixmap(os.path.abspath(image_path)),
            # 方法5: 相対パスに変換
            lambda: QPixmap(os.path.relpath(image_path))
        ]
        
        for i, load_method in enumerate(load_methods):
            try:
                temp_pixmap = load_method()
                if not temp_pixmap.isNull():
                    self._pixmap = temp_pixmap
                    print(f"[DEBUG IDW] 方法{i+1}で成功: サイズ {self._pixmap.width()}x{self._pixmap.height()}")
                    break
                else:
                    print(f"[DEBUG IDW] 方法{i+1}は失敗 (Null pixmap)")
            except Exception as e:
                print(f"[DEBUG IDW] 方法{i+1}でエラー: {e}")
        
        if self._pixmap.isNull():
            print("[DEBUG IDW] すべての方法で画像読み込みに失敗しました")
            # ダミー画像を作成
            self._pixmap = QPixmap(400, 300)
            self._pixmap.fill(QColor(220, 220, 220))
            painter = QPainter(self._pixmap)
            painter.setPen(QColor(255, 0, 0))
            painter.drawText(self._pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "画像読み込みエラー")
            painter.end()
            
        self._orig_size = (self._pixmap.width(), self._pixmap.height())
        self.update()

    def set_bboxes(self, bboxes):
        # 重複排除
        def is_same_box(b1, b2):
            if b1.cid != b2.cid or b1.cname != b2.cname or b1.role != b2.role:
                return False
            return all(abs(a-b) < 1.0 for a, b in zip(b1.xyxy, b2.xyxy))
        unique = []
        for b in bboxes:
            if not any(is_same_box(b, u) for u in unique):
                unique.append(b)
        self.bboxes = unique
        self.update()

    def set_roles(self, roles):
        self.roles = roles
        self.update()

    def set_selected_indices(self, indices):
        self.selected_indices = indices
        self.update()  # 必ず再描画

    def paintEvent(self, event):
        print(f"[DEBUG IDW] paintEvent called. self._pixmap is None: {self._pixmap is None}")
        if self._pixmap and not self._pixmap.isNull():
            print(f"[DEBUG IDW] paintEvent: Drawing pixmap {self._pixmap.width()}x{self._pixmap.height()}")
        elif self._pixmap and self._pixmap.isNull():
            print("[DEBUG IDW] paintEvent: self._pixmap is not None but isNull is true.")
        else:
            print("[DEBUG IDW] paintEvent: self._pixmap is None, drawing 'No Image'.")
        painter = QPainter(self)
        if self._pixmap:
            # ズーム倍率適用
            scaled_w = int(self._orig_size[0] * self._zoom_scale)
            scaled_h = int(self._orig_size[1] * self._zoom_scale)
            scaled_pixmap = self._pixmap.scaled(
                scaled_w, scaled_h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            disp_size = (scaled_pixmap.width(), scaled_pixmap.height())
            # 画像の描画位置（中央＋オフセット）
            x = (self.width() - disp_size[0]) // 2 + self._offset_x
            y = (self.height() - disp_size[1]) // 2 + self._offset_y
            painter.drawPixmap(x, y, scaled_pixmap)
            # bbox描画
            for idx, bbox in enumerate(self.bboxes):
                if idx in self.selected_indices:
                    color = QColor(0, 200, 255)
                elif bbox.role:
                    color = QColor(0, 200, 0)
                else:
                    color = QColor(255, 200, 0)
                pen = QPen(color, 4)
                painter.setPen(pen)
                if bbox.xyxy:
                    x1, y1, x2, y2 = map(int, bbox.get_scaled_xyxy(self._orig_size, disp_size))
                    x1 += x
                    x2 += x
                    y1 += y
                    y2 += y
                    painter.drawRect(x1, y1, x2 - x1, y2 - y1)
                    # ラベル描画
                    label_text = f"{bbox.cname} {bbox.conf:.2f}"
                    if bbox.role:
                        display = next((r['display'] for r in self.roles if r['label'] == bbox.role), bbox.role)
                        label_text += f" [{display}]"
                    font = painter.font()
                    metrics = painter.fontMetrics()
                    text_width = metrics.horizontalAdvance(label_text)
                    text_height = metrics.height()
                    bg_rect_x = x1
                    bg_rect_y = y1 - text_height if y1 - text_height > 0 else y1
                    bg_rect_w = text_width + 6
                    bg_rect_h = text_height
                    painter.setBrush(QColor(0, 0, 0, 180))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawRect(bg_rect_x, bg_rect_y, bg_rect_w, bg_rect_h)
                    painter.setPen(color)
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawText(bg_rect_x + 3, bg_rect_y + text_height - metrics.descent(), label_text)
            # 選択状態の枠
            if self.selected_indices and self.draw_global_selection_frame:
                pen = QPen(QColor(0, 120, 255), 6)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(2, 2, self.width()-4, self.height()-4)
        else:
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No Image")
        painter.end()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.RightButton:
            # 新規追加モード中はキャンセル
            if self._drawing:
                self._drawing = False
                self._draw_start = None
                self._draw_rect = None
                self.update()
                return
            # 右クリック時は選択状態を絶対に変更しない（複数選択維持）
            event.setAccepted(True)  # Qtのデフォルト挙動抑制
            self.box_right_clicked.emit(self.selected_indices.copy())
            self.update()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            x, y = event.position().toPoint().x(), event.position().toPoint().y()
            scaled_w = int(self._orig_size[0] * self._zoom_scale)
            scaled_h = int(self._orig_size[1] * self._zoom_scale)
            disp_size = (scaled_w, scaled_h)
            x0 = (self.width() - disp_size[0]) // 2 + self._offset_x
            y0 = (self.height() - disp_size[1]) // 2 + self._offset_y
            img_x = x - x0
            img_y = y - y0
            found_indices = []
            for idx, bbox in enumerate(self.bboxes):
                if bbox.xyxy and bbox.contains_point(img_x, img_y, self._orig_size, disp_size):
                    found_indices.append(idx)
            if found_indices:
                found = found_indices[0]
                if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    # Ctrl押下時はトグル
                    if found in self.selected_indices:
                        self.selected_indices.remove(found)
                    else:
                        self.selected_indices.append(found)
                else:
                    # 単独選択
                    self.selected_indices = [found]
                self.update()
                self.box_clicked.emit(self.selected_indices.copy())
                # 即座にJSON保存
                parent = self.parent()
                image_path = None
                while parent is not None:
                    if hasattr(parent, 'image_path'):
                        image_path = parent.image_path
                    if hasattr(parent, 'bboxes'):
                        parent.bboxes = self.bboxes.copy()
                    parent = parent.parent() if hasattr(parent, 'parent') else None
                if image_path:
                    save_image_cache(image_path, self.bboxes)
                return
            # ボックス外クリックで選択解除
            self.selected_indices = []
            self.update()
            return
        # 左シングルクリック以外は何もしない
        return

    def wheelEvent(self, event: QWheelEvent):
        angle = event.angleDelta().y()
        prev_idx = self._zoom_idx
        prev_scale = self._zoom_scale
        if angle > 0 and self._zoom_idx < len(self._zoom_levels) - 1:
            self._zoom_idx += 1
        elif angle < 0 and self._zoom_idx > 0:
            self._zoom_idx -= 1
        if self._zoom_idx != prev_idx:
            self._zoom_scale = self._zoom_levels[self._zoom_idx]
            self.update()
        super().wheelEvent(event)

    def showEvent(self, event):
        self.set_bboxes(self.bboxes)
        super().showEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.box_double_clicked.emit(self.selected_indices.copy())
        super().mouseDoubleClickEvent(event)

class EditableImageDisplayWidget(ImageDisplayWidget):
    bbox_committed = pyqtSignal()
    mouse_hint_changed = pyqtSignal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self._drawing = False
        self._draw_start = None
        self._draw_rect = None
        self._current_class_id = 0
        self._current_class_label = None
        self._current_class_index = None
        self.setMouseTracking(True)
        # 右クリック時のロール選択メニューも有効化
        # box_right_clickedは親Dialogでon_box_right_clickedに接続されている

    def set_current_class_id(self, class_id, class_label=None, class_index=None):
        self._current_class_id = class_id
        self._current_class_label = class_label
        self._current_class_index = class_index

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        if self._drawing and self._draw_rect:
            painter.setPen(QPen(QColor(255,0,0), 2, Qt.PenStyle.DashLine))
            painter.drawRect(self._draw_rect)
        painter.end()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.RightButton:
            # 新規追加モード中はキャンセル
            if self._drawing:
                self._drawing = False
                self._draw_start = None
                self._draw_rect = None
                self.update()
                return
            # 右クリック時は選択状態を絶対に変更しない（複数選択維持）
            event.setAccepted(True)  # Qtのデフォルト挙動抑制
            self.box_right_clicked.emit(self.selected_indices.copy())
            self.update()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            if self._drawing:
                # 新規追加モード中は選択不可
                return
            # 追加モードでなければ親クラスの左クリック処理
            super().mousePressEvent(event)
            return
        # 左シングルクリック以外は何もしない
        return

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self._pixmap:
            if not self._drawing:
                # ボックス追加開始
                self._drawing = True
                self._draw_start = event.position()
                self._draw_rect = QRectF(self._draw_start, self._draw_start)
            else:
                # ボックス確定
                if self._draw_rect:
                    from src.utils.bbox_utils import BoundingBox
                    scaled_w = int(self._orig_size[0] * self._zoom_scale)
                    scaled_h = int(self._orig_size[1] * self._zoom_scale)
                    disp_size = (scaled_w, scaled_h)
                    x0 = (self.width() - disp_size[0]) // 2 + self._offset_x
                    y0 = (self.height() - disp_size[1]) // 2 + self._offset_y
                    rect = self._draw_rect.translated(-x0, -y0)
                    scale_x = self._orig_size[0] / disp_size[0] if disp_size[0] else 1
                    scale_y = self._orig_size[1] / disp_size[1] if disp_size[1] else 1
                    x1 = rect.left() * scale_x
                    y1 = rect.top() * scale_y
                    x2 = rect.right() * scale_x
                    y2 = rect.bottom() * scale_y
                    if abs(x2-x1) > 5 and abs(y2-y1) > 5:
                        cid = self._current_class_index or 0
                        cname = self._current_class_label or ''
                        conf = 1.0
                        role = self._current_class_id
                        # 重複チェック
                        def is_same_box(b):
                            if b.cid != cid or b.cname != cname or b.role != role:
                                return False
                            bx1, by1, bx2, by2 = b.xyxy
                            return all(abs(a-b) < 1.0 for a, b in zip([x1, y1, x2, y2], [bx1, by1, bx2, by2]))
                        if not any(is_same_box(b) for b in self.bboxes):
                            self.bboxes.append(BoundingBox(cid, cname, conf, [x1, y1, x2, y2], role))
                            if hasattr(self, 'bbox_committed'):
                                self.bbox_committed.emit()
                # 状態リセットは必ず実行
                self._drawing = False
                self._draw_start = None
                self._draw_rect = None
                self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drawing and self._draw_start:
            end = event.position()
            self._draw_rect = QRectF(self._draw_start, end).normalized()
            self.update()
        # superは呼ばない 

    def enterEvent(self, event):
        self.mouse_hint_changed.emit("左ダブルクリック=追加/確定, 右クリック=キャンセル, 左クリック=選択, 右クリック=削除")
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.mouse_hint_changed.emit("")
        super().leaveEvent(event)