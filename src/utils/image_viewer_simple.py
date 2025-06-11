#!/usr/bin/env python3
"""
シンプルな画像ビューワー（安定性重視）
"""
import sys
import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem,
    QApplication
)
from PyQt6.QtCore import Qt, QRectF, pyqtSignal
from PyQt6.QtGui import QPixmap, QPen, QColor, QFont


class SimpleImageViewerDialog(QDialog):
    """シンプルな画像ビューワーダイアログ"""
    
    # 画像移動用シグナル
    prev_image_requested = pyqtSignal()
    next_image_requested = pyqtSignal()
    
    def __init__(self, image_path, detections=None, parent=None):
        """初期化"""
        super().__init__(parent)
        self.image_path = image_path
        self.detections = detections or []
        
        self.setWindowTitle(f"簡易ビューワー: {Path(image_path).name}")
        self.resize(800, 600)
        
        # UIの初期化
        self.setup_ui()
        
        # 画像のロード
        self.load_image()
    
    def setup_ui(self):
        """UIの初期化"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 画像表示領域
        self.view = QGraphicsView()
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)
        layout.addWidget(self.view)
        
        # ボタン領域
        button_layout = QHBoxLayout()
        
        prev_btn = QPushButton("前へ")
        prev_btn.clicked.connect(self.prev_image_requested)
        
        next_btn = QPushButton("次へ")
        next_btn.clicked.connect(self.next_image_requested)
        
        close_btn = QPushButton("閉じる")
        close_btn.clicked.connect(self.close)
        
        button_layout.addWidget(prev_btn)
        button_layout.addWidget(next_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def load_image(self):
        """画像の読み込み"""
        try:
            # シーンをクリア
            self.scene.clear()
            
            # 画像が存在するか確認
            if not os.path.exists(self.image_path):
                text_item = self.scene.addText(f"画像が見つかりません: {self.image_path}")
                return
            
            # 画像を読み込み
            pixmap = QPixmap(self.image_path)
            if pixmap.isNull():
                text_item = self.scene.addText(f"画像を読み込めません: {self.image_path}")
                return
            
            # 画像をシーンに追加
            self.pixmap_item = self.scene.addPixmap(pixmap)
            
            # シーンの大きさを画像に合わせる
            self.scene.setSceneRect(QRectF(0, 0, pixmap.width(), pixmap.height()))
            
            # 画像が全体表示されるように調整
            self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
            
            # 検出結果を描画
            self.draw_detections()
            
        except Exception as e:
            print(f"画像読み込み中にエラーが発生しました: {e}")
            
    def draw_detections(self):
        """検出結果の描画（シンプルな実装）"""
        try:
            if not self.detections:
                return
                
            for det in self.detections:
                try:
                    # 座標を取得
                    xyxy = det.get('xyxy')
                    if not xyxy or len(xyxy) != 4:
                        continue
                        
                    x1, y1, x2, y2 = xyxy
                    
                    # クラス情報
                    cls_id = det.get('class', 0)
                    cls_name = det.get('class_name', f"class_{cls_id}")
                    conf = det.get('confidence', 0.0)
                    
                    # 単純な色（クラスIDに基づく）
                    color = QColor(
                        (cls_id * 50 + 100) % 200 + 55,  # R
                        (cls_id * 80 + 50) % 200 + 55,   # G
                        (cls_id * 100 + 150) % 200 + 55  # B
                    )
                    
                    # バウンディングボックスを描画
                    rect = QGraphicsRectItem(x1, y1, x2-x1, y2-y1)
                    rect.setPen(QPen(color, 2))
                    self.scene.addItem(rect)
                    
                    # ラベルテキスト
                    label = f"{cls_name}: {conf:.2f}"
                    text = QGraphicsTextItem(label)
                    text.setPos(x1, y1 - 20)
                    text.setDefaultTextColor(color)
                    
                    # テキストに簡単なフォント設定
                    font = QFont()
                    font.setBold(True)
                    text.setFont(font)
                    
                    self.scene.addItem(text)
                    
                except Exception as e:
                    print(f"検出結果の描画中にエラー: {e}")
                    
        except Exception as e:
            print(f"検出結果描画中に例外が発生: {e}")
    
    def resizeEvent(self, event):
        """ウィンドウリサイズ時に画像を調整"""
        if hasattr(self, 'scene') and hasattr(self, 'view'):
            self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        super().resizeEvent(event)


# 単体テスト用
if __name__ == "__main__":
    # テスト用データ
    test_image = "test.jpg"  # 既存の画像がなければエラーメッセージが表示される
    
    test_detections = [
        {
            "class": 0,
            "class_name": "person",
            "confidence": 0.85,
            "xyxy": [50, 50, 150, 200]
        }
    ]
    
    app = QApplication(sys.argv)
    
    # コマンドライン引数で画像パスを指定可能
    if len(sys.argv) > 1:
        test_image = sys.argv[1]
    
    # ビューワーを表示
    viewer = SimpleImageViewerDialog(test_image, test_detections)
    viewer.show()
    
    sys.exit(app.exec()) 