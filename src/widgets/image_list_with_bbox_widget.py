from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QMenu, QPushButton, QFileDialog, QMessageBox
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QPen
from PyQt6.QtCore import QSize, Qt, QThread, pyqtSignal, QObject
import os, json
from .thumb_widget import ThumbWorker

class ImageListWithBboxWidget(QWidget):
    def __init__(self, json_path, proj_name=None, parent=None):
        super().__init__(parent)
        self.json_path = json_path
        self.proj_name = proj_name or ""
        self.setWindowTitle(f"{proj_name} の画像サムネイル＋bbox一覧")
        vbox = QVBoxLayout(self)
        self.list_widget = QListWidget(self)
        self.list_widget.setViewMode(QListWidget.ViewMode.IconMode)
        self.list_widget.setIconSize(QSize(180, 180))
        self.list_widget.setGridSize(QSize(200, 220))
        self.list_widget.setWrapping(True)
        self.list_widget.setSpacing(10)
        self.list_widget.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        vbox.addWidget(self.list_widget)
        self.setLayout(vbox)
        # 右クリックメニュー
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.on_context_menu)
        # サムネイル生成
        self._start_thumb_thread()
        # 閉じるボタン（ダイアログ用）
        self.close_btn = QPushButton("閉じる", self)
        self.close_btn.clicked.connect(self._on_close)
        vbox.addWidget(self.close_btn)

    def _start_thumb_thread(self):
        if not os.path.exists(self.json_path):
            return
        with open(self.json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            images = data
        elif isinstance(data, dict):
            images = data.get('images', [])
        else:
            images = []
        self.worker = ThumbWorker(images, self)
        self.thread = QThread()  # 親なし
        self.worker.moveToThread(self.thread)
        self.worker.thumb_ready.connect(self.add_thumb)
        self.thread.started.connect(self.worker.run)
        # workerのrun終了時にスレッドをquitする
        class _ThreadFinisher(QObject):
            finished = pyqtSignal()
        self._finisher = _ThreadFinisher()
        def on_worker_finished():
            self.thread.quit()
        self._finisher.finished.connect(on_worker_finished)
        self.worker.finished = self._finisher.finished.emit  # worker内でself.finished()を呼ぶ
        self.thread.start()

    def _stop_thread(self):
        if hasattr(self, 'thread') and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()

    def _on_close(self):
        self._stop_thread()
        self.close()

    def add_thumb(self, idx, img_path, temp_img_path, bbox_objs, roles):
        if not img_path or not os.path.exists(img_path):
            return
        pixmap = QPixmap(img_path)
        if pixmap.isNull():
            return
        # bbox描画
        if bbox_objs:
            painter = QPainter(pixmap)
            pen = QPen(Qt.GlobalColor.red)
            pen.setWidth(3)
            painter.setPen(pen)
            for bbox in bbox_objs:
                if all(k in bbox for k in ("x", "y", "w", "h")):
                    x, y, w, h = bbox["x"], bbox["y"], bbox["w"], bbox["h"]
                    painter.drawRect(int(x), int(y), int(w), int(h))
                elif all(k in bbox for k in ("xmin", "ymin", "xmax", "ymax")):
                    x, y, w, h = bbox["xmin"], bbox["ymin"], bbox["xmax"]-bbox["xmin"], bbox["ymax"]-bbox["ymin"]
                    painter.drawRect(int(x), int(y), int(w), int(h))
            painter.end()
        thumb_pixmap = pixmap.scaled(180, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        icon = QIcon(thumb_pixmap)
        label_text = os.path.basename(img_path)
        if roles:
            label_text += "\n" + ", ".join(map(str, roles))
        item = QListWidgetItem(icon, label_text)
        item.setData(Qt.ItemDataRole.UserRole, img_path)
        self.list_widget.addItem(item)

    def on_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        menu = QMenu(self.list_widget)
        act_info = menu.addAction("画像情報を表示")
        act_export = menu.addAction("YOLOデータセット変換")
        act_aug = menu.addAction("データ拡張")
        act_result = menu.addAction("変換リザルト表示")
        act = menu.exec(self.list_widget.mapToGlobal(pos))
        img_path = item.data(Qt.ItemDataRole.UserRole)
        if act == act_info:
            QMessageBox.information(self.list_widget, "画像情報", f"パス: {img_path}")
        elif act == act_export:
            from src.utils.image_ops import convert_image_to_yolo_dataset
            json_path = os.path.splitext(img_path)[0] + ".json"
            output_dir = QFileDialog.getExistingDirectory(self.list_widget, "出力先ディレクトリ選択")
            if not output_dir:
                return
            result = convert_image_to_yolo_dataset(json_path, output_dir)
            QMessageBox.information(self.list_widget, "変換完了", f"YOLOデータセット変換が完了しました\n{result}")
        elif act == act_aug:
            from src.utils.image_ops import augment_image_dataset
            img_dir = os.path.dirname(img_path)
            label_dir = os.path.dirname(os.path.splitext(img_path)[0] + ".txt")
            output_dir = QFileDialog.getExistingDirectory(self.list_widget, "拡張データ出力先ディレクトリ選択")
            if not output_dir:
                return
            result = augment_image_dataset(img_dir, label_dir, output_dir)
            QMessageBox.information(self.list_widget, "拡張完了", f"データ拡張が完了しました\n{result}")
        elif act == act_result:
            output_dir = QFileDialog.getExistingDirectory(self.list_widget, "リザルト出力先ディレクトリ選択")
            if not output_dir:
                return
            from src.yolo_dataset_exporter import YoloDatasetExporter
            exporter = YoloDatasetExporter([json_path], output_dir=output_dir)
            result = exporter.export(mode='all', force_flush=False)
            # リザルト表示は親ウィジェット側で拡張可
            QMessageBox.information(self.list_widget, "リザルト", str(result))

    def closeEvent(self, event):
        self._stop_thread()
        super().closeEvent(event)

    def __del__(self):
        self._stop_thread() 