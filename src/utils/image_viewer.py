#!/usr/bin/env python3
"""
バウンディングボックス付き画像ビューワー
"""
import sys
import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QScrollArea, QWidget, QSizePolicy,
    QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QRectF, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QPen, QColor, QFont, QWheelEvent, QPainter, QBrush


class ImageViewerDialog(QDialog):
    """画像ビューワーダイアログ"""
    
    # 新しいシグナルを追加して前後の画像に移動するためのシグナルを定義
    prev_image_requested = pyqtSignal()
    next_image_requested = pyqtSignal()
    
    def __init__(self, image_path, detections=None, parent=None):
        """
        初期化
        
        Args:
            image_path: 表示する画像のパス
            detections: 検出結果のリスト (オプション)
            parent: 親ウィジェット
        """
        super().__init__(parent)
        self.image_path = image_path
        self.detections = detections or []
        self.use_glow_effect = False  # グロー効果フラグ（安定性のためデフォルトでオフ）
        self.detection_items = []  # 検出表示用アイテムのリスト
        
        # ヘッドレスモードの検出
        self.is_headless = False
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen" or \
           os.environ.get("QT_FORCE_HEADLESS") == "1":
            self.is_headless = True
            # ヘッドレスモードではグラフィックス関連の処理を最小限に
            self.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        
        self.setWindowTitle(f"画像ビューワー: {Path(image_path).name}")
        self.resize(800, 600)
        
        self.setup_ui()
        self.load_image()
    
    def setup_ui(self):
        """UIの初期化"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # 画像表示エリア
        self.graphics_view = ZoomableGraphicsView(is_headless=self.is_headless)
        self.scene = QGraphicsScene()
        self.graphics_view.setScene(self.scene)
        
        # マウスホイールでの画像切り替えのためのシグナルを接続
        self.graphics_view.prev_image_requested.connect(self.prev_image_requested)
        self.graphics_view.next_image_requested.connect(self.next_image_requested)
        
        main_layout.addWidget(self.graphics_view)
        
        # ボタンエリア
        button_layout = QHBoxLayout()
        
        # 前の画像ボタン
        prev_btn = QPushButton("前の画像")
        prev_btn.clicked.connect(self.prev_image_requested)
        
        # 次の画像ボタン
        next_btn = QPushButton("次の画像")
        next_btn.clicked.connect(self.next_image_requested)
        
        # 閉じるボタン
        close_btn = QPushButton("閉じる")
        close_btn.clicked.connect(self.close)
        
        # 元のサイズに戻すボタン
        reset_btn = QPushButton("元のサイズ")
        reset_btn.clicked.connect(self.reset_zoom)
        
        # 検出情報表示/非表示ボタン
        self.toggle_det_btn = QPushButton("検出情報を非表示")
        self.toggle_det_btn.clicked.connect(self.toggle_detections)
        self.show_detections = True
        
        button_layout.addWidget(prev_btn)
        button_layout.addWidget(next_btn)
        button_layout.addWidget(self.toggle_det_btn)
        button_layout.addWidget(reset_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        main_layout.addLayout(button_layout)
    
    def load_image(self):
        """画像を読み込んでシーンに追加"""
        # ヘッドレスモードでQPixmap作成が失敗する可能性があるため例外処理
        try:
            if not os.path.exists(self.image_path):
                self.scene.addText(f"画像が見つかりません: {self.image_path}")
                return
            
            # 画像をロード
            pixmap = QPixmap(self.image_path)
            if pixmap.isNull():
                self.scene.addText(f"画像を読み込めません: {self.image_path}")
                return
            
            # 画像をシーンに追加
            self.scene.clear()
            self.pixmap_item = self.scene.addPixmap(pixmap)
            
            # シーンの大きさを画像に合わせる
            self.scene.setSceneRect(QRectF(0, 0, pixmap.width(), pixmap.height()))
            
            # バウンディングボックスを描画
            self.draw_detections()
            
            # 表示を最適化
            self.reset_zoom()
            
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"画像読み込み中にエラーが発生: {e}", exc_info=True)
            self.scene.clear()
            self.scene.addText(f"画像処理エラー: {str(e)}")
        
    def draw_detections(self):
        """検出結果を蛍光色で描画（グロー効果なし）"""
        if not self.detections or not self.show_detections:
            return

        # 前回の検出表示アイテムをすべて削除
        for item in self.detection_items:
            self.scene.removeItem(item)
        self.detection_items.clear()

        for det in self.detections:
            xy = det.get('xyxy')
            if not xy:
                continue
            x1, y1, x2, y2 = xy
            w, h = x2 - x1, y2 - y1

            class_id   = det.get('class', 0)
            class_name = det.get('class_name', f"class_{class_id}")
            conf       = det.get('confidence', 0.0)

            # ■ HSV で彩度・輝度 100% の蛍光色を生成
            hue   = (class_id * 47) % 360
            color = QColor.fromHsv(hue, 255, 255)

            # ■ 太い実線ペン
            pen = QPen(color, 3)
            pen.setStyle(Qt.PenStyle.SolidLine)

            # ■ 矩形の描画
            rect = QGraphicsRectItem(x1, y1, w, h)
            rect.setPen(pen)
            # 半透明のフィルを加えたい場合は以下を有効化（アルファ値 40/255）
            rect.setBrush(QColor(color.red(), color.green(), color.blue(), 40))
            self.scene.addItem(rect)
            self.detection_items.append(rect)

            # ■ ラベルテキスト
            label = f"{class_name}: {conf:.2f}"
            text = QGraphicsTextItem(label)
            text.setDefaultTextColor(color)
            font = QFont()
            font.setPointSize(12)
            font.setBold(True)
            text.setFont(font)
            text.setPos(x1, y1 - 20)
            
            # ■ 背景の半透明黒四角（ラベルの可読性向上）
            bg = QGraphicsRectItem(text.boundingRect())
            bg.setBrush(QColor(0, 0, 0, 160))
            bg.setPos(text.pos())
            bg.setPen(QPen(Qt.PenStyle.NoPen))
            
            self.scene.addItem(bg)
            self.detection_items.append(bg)
            
            self.scene.addItem(text)
            self.detection_items.append(text)

    def toggle_detections(self):
        """検出情報の表示/非表示を切り替え"""
        self.show_detections = not self.show_detections
        
        # ボタンのテキストを更新
        if self.show_detections:
            self.toggle_det_btn.setText("検出情報を非表示")
        else:
            self.toggle_det_btn.setText("検出情報を表示")
        
        # 画像を再読み込み
        self.load_image()
    
    def reset_zoom(self):
        """ズームをリセットして画像全体を表示"""
        self.graphics_view.resetTransform()
        self.graphics_view.setSceneRect(self.scene.sceneRect())
        self.graphics_view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)


class ZoomableGraphicsView(QGraphicsView):
    """ズームとパン操作可能なグラフィックスビュー"""
    
    # 新しいシグナルを追加して前後の画像に移動することを親に知らせる
    prev_image_requested = pyqtSignal()
    next_image_requested = pyqtSignal()
    
    def __init__(self, parent=None, is_headless=False):
        super().__init__(parent)
        self.is_headless = is_headless
        
        # ヘッドレスモードでは描画設定を最適化
        if not self.is_headless:
            self.setRenderHint(QPainter.RenderHint.Antialiasing)
            self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        else:
            # ヘッドレスモードでは高負荷なレンダリングオプションをオフ
            self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing, True)
            self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontSavePainterState, True)
        
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setMinimumSize(200, 200)
        
        # 拡大率
        self.zoom_factor = 1.15
        
        # ShiftキーとCtrlキーの状態
        self.shift_pressed = False
        self.ctrl_pressed = False
    
    def wheelEvent(self, event):
        """マウスホイールイベント（ズームまたは画像切り替え）"""
        # Shiftキーが押されている場合、前後の画像に移動
        if self.shift_pressed:
            if event.angleDelta().y() > 0:
                # 前の画像に移動
                self.prev_image_requested.emit()
            else:
                # 次の画像に移動
                self.next_image_requested.emit()
        else:
            # 通常のズーム動作
            if event.angleDelta().y() > 0:
                # ズームイン
                self.scale(self.zoom_factor, self.zoom_factor)
            else:
                # ズームアウト
                self.scale(1.0 / self.zoom_factor, 1.0 / self.zoom_factor)
    
    def keyPressEvent(self, event):
        """キー押下イベント"""
        if event.key() == Qt.Key.Key_Shift:
            self.shift_pressed = True
        elif event.key() == Qt.Key.Key_Control:
            self.ctrl_pressed = True
        super().keyPressEvent(event)
    
    def keyReleaseEvent(self, event):
        """キー解放イベント"""
        if event.key() == Qt.Key.Key_Shift:
            self.shift_pressed = False
        elif event.key() == Qt.Key.Key_Control:
            self.ctrl_pressed = False
        super().keyReleaseEvent(event)


# 単体テスト用
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # テスト用検出結果
    test_detections = [
        {
            "class": 0,
            "class_name": "person",
            "confidence": 0.85,
            "xyxy": [100, 100, 300, 500]
        },
        {
            "class": 2,
            "class_name": "car",
            "confidence": 0.75,
            "xyxy": [400, 300, 600, 450]
        }
    ]
    
    # テスト画像パス
    if len(sys.argv) > 1:
        test_image = sys.argv[1]
    else:
        test_image = "test.jpg"  # デフォルトのテスト画像
    
    # ダイアログを表示
    dialog = ImageViewerDialog(test_image, test_detections)
    dialog.exec() 