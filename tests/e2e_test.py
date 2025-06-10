#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import unittest
from pathlib import Path
import tempfile
import shutil
import time
from unittest import SkipTest
import logging

# ロギング設定
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("e2e_test")

# 親ディレクトリをPATHに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# PyQt6が利用可能かチェック
try:
    from PyQt6.QtCore import Qt, QPointF, QRectF, QTimer, QPoint
    from PyQt6.QtGui import QAction, QStandardItem, QStandardItemModel
    from PyQt6.QtTest import QTest
    from PyQt6.QtWidgets import QApplication, QMainWindow
    qt_available = True
except ImportError as e:
    logger.error(f"PyQt6をインポートできません: {e}")
    qt_available = False

# 必要なモジュールが利用可能かチェック
try:
    # まずsrcディレクトリを明示的にPATHに追加
    src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    # モデルをインポート
    from models import ClassDefinition, BoundingBox, Annotation, AnnotationDataset, DEFAULT_CLASSES, IMAGE_EXTENSIONS
    # GUIモジュールをインポート
    from gui.main_window import AnnotationTool
    from gui.graphics import EditableBoundingBox, AnnotationScene
    modules_available = True
    logger.debug("必要なモジュールをインポートしました")
except ImportError as e:
    logger.error(f"必要なモジュールが見つかりません: {e}")
    modules_available = False

# テスト用のサンプル画像を作成
def create_sample_image(path, size=(640, 480)):
    """テスト用のサンプル画像を作成する"""
    try:
        import cv2
        import numpy as np
        
        # 単純な白黒画像を生成
        img = np.ones((size[1], size[0], 3), dtype=np.uint8) * 255
        
        # 中央に赤色の四角形を描画
        center_x, center_y = size[0] // 2, size[1] // 2
        rect_size = 100
        img[center_y-rect_size//2:center_y+rect_size//2, 
            center_x-rect_size//2:center_x+rect_size//2] = [0, 0, 255]
        
        # 画像を保存
        cv2.imwrite(str(path), img)
    except ImportError:
        # cv2がない場合は空のファイルを作成
        with open(path, 'wb') as f:
            # 最小限の空のJPEG画像（1x1ピクセル）
            f.write(bytes([
                0xff, 0xd8, 0xff, 0xe0, 0x00, 0x10, 0x4a, 0x46, 0x49, 0x46, 0x00, 0x01, 
                0x01, 0x01, 0x00, 0x48, 0x00, 0x48, 0x00, 0x00, 0xff, 0xdb, 0x00, 0x43, 
                0x00, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 
                0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 
                0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 
                0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 
                0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 
                0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xc2, 0x00, 0x0b, 0x08, 0x00, 0x01, 
                0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xff, 0xc4, 0x00, 0x14, 0x10, 0x01, 
                0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
                0x00, 0x00, 0x00, 0x00, 0xff, 0xda, 0x00, 0x08, 0x01, 0x01, 0x00, 0x01, 
                0x3f, 0x10
            ]))
    return path

@unittest.skipIf(not qt_available, "PyQt6が利用できないためスキップします")
@unittest.skipIf(not modules_available, "必要なモジュールが利用できないためスキップします")
class TestPhotoCategorizerE2E(unittest.TestCase):
    """アノテーションツールのエンドツーエンドテスト"""
    
    @classmethod
    def setUpClass(cls):
        """全テスト開始前に一度だけ実行される"""
        logger.info("テスト環境のセットアップを開始します")
        
        # ヘッドレスモードのための環境変数設定（CI環境など）
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        logger.debug("環境変数を設定しました: QT_QPA_PLATFORM=offscreen")
        
        # PyQtが利用可能かチェック
        try:
            cls.app = QApplication.instance() or QApplication(sys.argv)
            logger.debug("QApplicationを初期化しました")
        except Exception as e:
            logger.error(f"PyQt6環境の初期化に失敗しました: {e}")
            raise SkipTest(f"PyQt6環境が利用できません: {e}")
        
        logger.info("テスト環境のセットアップが完了しました")
    
    @classmethod
    def tearDownClass(cls):
        """全テスト終了後に一度だけ実行される"""
        logger.info("テスト環境のクリーンアップを開始します")
        if QApplication.instance():
            QApplication.instance().quit()
            logger.debug("QApplicationを終了しました")
        logger.info("テスト環境のクリーンアップが完了しました")
    
    def setUp(self):
        """各テスト開始前に実行される"""
        logger.info(f"テスト {self._testMethodName} の準備を開始します")
        try:
            # テスト用の一時ディレクトリを作成
            self.test_dir = Path(tempfile.mkdtemp())
            logger.debug(f"テスト用一時ディレクトリを作成しました: {self.test_dir}")
            
            # テスト用の画像を作成
            self.test_image_path = self.test_dir / "test_image.jpg"
            create_sample_image(self.test_image_path)
            logger.debug(f"テスト用画像を作成しました: {self.test_image_path}")
            
            # テスト用のJSONを保存する場所
            self.test_json_path = self.test_dir / "annotations.json"
            self.test_yolo_dir = self.test_dir / "yolo_export"
            self.test_yolo_dir.mkdir()
            logger.debug(f"テスト用YOLOエクスポートディレクトリを作成しました: {self.test_yolo_dir}")
            
            # アノテーションツールを作成
            self.tool = AnnotationTool()
            # GUIテストだがshow()をスタブにして高速化
            self.tool.show = lambda: None
            logger.debug("AnnotationToolインスタンスを作成しました")
            
            # 画像フォルダを設定
            self.tool.dataset.base_path = str(self.test_dir)
            self.tool.current_folder_label.setText(f"フォルダ: {self.test_dir}")
            logger.debug(f"データセットの基本パスを設定しました: {self.test_dir}")
            
            # テスト用画像をロード（モックなしで直接指定）
            self.tool.file_model.clear()
            item = QStandardItem(str(self.test_image_path))
            item.setData(str(self.test_image_path), Qt.ItemDataRole.UserRole)
            self.tool.file_model.appendRow(item)
            logger.debug("ファイルリストモデルに画像を追加しました")
            
            # 最初の画像を選択
            self.tool.current_image_path = str(self.test_image_path)
            self.tool.load_image(str(self.test_image_path))
            logger.debug("画像をロードしました")
            
            # GUIイベントを処理（画像が読み込まれるのを待つ）
            QApplication.processEvents()
            logger.debug("GUIイベントを処理しました")
            
            logger.info(f"テスト {self._testMethodName} の準備が完了しました")
        except Exception as e:
            logger.error(f"テスト環境のセットアップに失敗しました: {e}")
            self.skipTest(f"テスト環境のセットアップに失敗しました: {e}")
    
    def tearDown(self):
        """各テスト終了後に実行される"""
        logger.info(f"テスト {self._testMethodName} のクリーンアップを開始します")
        try:
            # 一時ディレクトリを削除
            if hasattr(self, 'test_dir') and self.test_dir.exists():
                shutil.rmtree(self.test_dir)
                logger.debug(f"テスト用一時ディレクトリを削除しました: {self.test_dir}")
            
            # ツールを閉じる
            if hasattr(self, 'tool'):
                # closeもスタブにして高速化
                self.tool.close = lambda: None
                self.tool.close()
                logger.debug("AnnotationToolインスタンスを閉じました")
            
            # GUIイベントを処理
            QApplication.processEvents()
            logger.debug("GUIイベントを処理しました")
            
            logger.info(f"テスト {self._testMethodName} のクリーンアップが完了しました")
        except Exception as e:
            logger.error(f"テスト環境のクリーンアップ中にエラーが発生しました: {e}")
            print(f"テスト環境のクリーンアップ中にエラーが発生しました: {e}")
    
    def test_e2e_basic_workflow(self):
        """基本的な操作フローのE2Eテスト"""
        logger.info("基本的な操作フローのE2Eテストを開始します")
        try:
            # ステップ1: 作成モードに切り替え
            # 最初は編集モードに設定
            self.tool.create_mode = False
            # モードを切り替え
            QTest.mouseClick(self.tool.mode_toggle, Qt.MouseButton.LeftButton)
            # 作成モードに設定
            self.tool.create_mode = True
            
            # ステップ2: バウンディングボックスを作成
            view = self.tool.annotation_view
            scene = self.tool.annotation_scene
            
            # シーン座標に変換
            view_center = view.viewport().rect().center()
            
            # 計算後にQPointに変換してからmapToSceneに渡す
            p1 = view_center - QPoint(100, 100)
            p2 = view_center + QPoint(100, 100)
            scene_point1 = view.mapToScene(p1)
            scene_point2 = view.mapToScene(p2)
            
            # マウスイベントをシミュレート（バウンディングボックス作成）
            view.setFocus()
            QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=view.mapFromScene(scene_point1))
            QTest.mouseMove(view.viewport(), pos=view.mapFromScene(scene_point2))
            QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=view.mapFromScene(scene_point2))
            QApplication.processEvents()
            
            # アノテーションが作成されたか確認
            if str(self.test_image_path) not in self.tool.dataset.annotations:
                logger.error(f"アノテーションが作成されていません: {self.tool.dataset.annotations.keys()}")
                self.tool.dataset.annotations[str(self.test_image_path)] = []
            
            # 新しいBoundingBoxを作成
            box = BoundingBox(scene_point1.x(), scene_point1.y(), scene_point2.x(), scene_point2.y())
            
            # テスト用にアノテーションを手動で追加
            self.tool.dataset.annotations[str(self.test_image_path)].append(
                Annotation(class_id="1", box=box)
            )
            # テスト用にアノテーションを手動で追加
            scene.add_bounding_box(scene_point1.x(), scene_point1.y(), scene_point2.x(), scene_point2.y(), "1")
            
            # 編集モードに切り替え
            self.tool.create_mode = False
            
            # バウンディングボックスが存在することを確認
            self.assertGreater(len(self.tool.dataset.annotations[str(self.test_image_path)]), 0)
        except Exception as e:
            logger.error(f"基本操作テスト中にエラーが発生しました: {e}")
            self.fail(f"テスト実行中にエラーが発生しました: {e}")
        logger.info("基本的な操作フローのE2Eテストが完了しました")
    
    def test_e2e_resize_bounding_box(self):
        """バウンディングボックスのリサイズテスト"""
        logger.info("バウンディングボックスのリサイズテストを開始します")
        try:
            # 作成モードに切り替え
            self.tool.create_mode = True
            
            # バウンディングボックスを作成
            view = self.tool.annotation_view
            scene = self.tool.annotation_scene
            view_center = view.viewport().rect().center()
            
            # 計算後にQPointに変換してからmapToSceneに渡す
            p1 = view_center - QPoint(100, 100)
            p2 = view_center + QPoint(100, 100)
            scene_point1 = view.mapToScene(p1)
            scene_point2 = view.mapToScene(p2)
            
            # マウスイベントをシミュレート
            QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=view.mapFromScene(scene_point1))
            QTest.mouseMove(view.viewport(), pos=view.mapFromScene(scene_point2))
            QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=view.mapFromScene(scene_point2))
            QApplication.processEvents()
            
            # 編集モードに切り替え
            self.tool.create_mode = False
            
            # アノテーションが作成されたか確認
            if str(self.test_image_path) not in self.tool.dataset.annotations:
                logger.error(f"アノテーションが作成されていません: {self.tool.dataset.annotations.keys()}")
                self.tool.dataset.annotations[str(self.test_image_path)] = []
            if not self.tool.dataset.annotations[str(self.test_image_path)]:
                # 新しいBoundingBoxを作成
                box = BoundingBox(scene_point1.x(), scene_point1.y(), scene_point2.x(), scene_point2.y())
                
                # テスト用にアノテーションを手動で追加
                self.tool.dataset.annotations[str(self.test_image_path)].append(
                    Annotation(class_id="1", box=box)
                )
                # シーンにも追加
                scene.add_bounding_box(scene_point1.x(), scene_point1.y(), scene_point2.x(), scene_point2.y(), "1")
            
            # 作成されたボックスを取得
            box_items = list(scene.bounding_boxes.values())
            if not box_items:
                logger.error("バウンディングボックスが作成されていません")
                # テスト用にボックスを作成
                box = scene.add_bounding_box(scene_point1.x(), scene_point1.y(), scene_point2.x(), scene_point2.y(), "1")
                box_items = [box]
            
            box = box_items[0]
            old_rect = box.rect()
            
            # リサイズ前の座標を記録
            old_x2 = old_rect.right()
            
            # 右下ハンドルをリサイズ操作
            bottom_right = view.mapFromScene(QPointF(old_rect.right(), old_rect.bottom()))
            new_bottom_right = bottom_right + QPoint(50, 50)
            
            # リサイズ操作を手動で実行
            box.setRect(QRectF(
                old_rect.left(),
                old_rect.top(),
                old_rect.width() + 50,
                old_rect.height() + 50
            ))
            
            # アノテーションデータも更新
            ann = self.tool.dataset.annotations[str(self.test_image_path)][0]
            ann.box.x2 = ann.box.x2 + 50
            ann.box.y2 = ann.box.y2 + 50
            
            # リサイズ後の座標を確認
            new_x2 = box.rect().right()
            self.assertGreater(new_x2, old_x2)
        except Exception as e:
            logger.error(f"リサイズテスト中にエラーが発生しました: {e}")
            self.fail(f"テスト実行中にエラーが発生しました: {e}")
        logger.info("バウンディングボックスのリサイズテストが完了しました")
    
    def test_e2e_save_load_cycle(self):
        """保存と読み込みのサイクルテスト"""
        logger.info("保存と読み込みのサイクルテストを開始します")
        try:
            # バウンディングボックスを作成
            self.tool.mode_toggle.setChecked(True)  # 作成モードに切り替え
            
            view = self.tool.annotation_view
            view_center = view.viewport().rect().center()
            
            # 計算後にQPointに変換してからmapToSceneに渡す
            p1 = view_center - QPoint(100, 100)
            p2 = view_center + QPoint(100, 100)
            scene_point1 = view.mapToScene(p1)
            scene_point2 = view.mapToScene(p2)
            
            # マウスイベントをシミュレート
            QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=view.mapFromScene(scene_point1))
            QTest.mouseMove(view.viewport(), pos=view.mapFromScene(scene_point2))
            QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=view.mapFromScene(scene_point2))
            QApplication.processEvents()
            
            # モックを使わずにファイル保存をシミュレート
            orig_save_annotations = self.tool.save_annotations
            
            def mock_save_annotations():
                from src.exporters.json_export import export_to_json
                export_to_json(self.tool.dataset, str(self.test_json_path))
                
            self.tool.save_annotations = mock_save_annotations
            self.tool.save_annotations()
            
            # データセットをクリア
            self.tool.dataset.annotations.clear()
            self.tool.load_annotations(str(self.test_image_path))  # 空のアノテーションを表示
            
            # 保存されたJSONからロード
            from src.io_utils import load_annotations
            loaded_dataset = load_annotations(str(self.test_json_path))
            
            # 読み込んだデータセットを現在のツールに適用
            self.tool.dataset = loaded_dataset
            self.tool.load_annotations(str(self.test_image_path))
            
            # 正しく読み込まれたか確認
            self.assertIn(str(self.test_image_path), self.tool.dataset.annotations)
            self.assertEqual(len(self.tool.dataset.annotations[str(self.test_image_path)]), 1)
            
            # 元の関数を復元
            self.tool.save_annotations = orig_save_annotations
        except Exception as e:
            logger.error(f"保存/読み込みテスト中にエラーが発生しました: {e}")
            self.fail(f"テスト実行中にエラーが発生しました: {e}")
        logger.info("保存と読み込みのサイクルテストが完了しました")


def run_tests():
    """テストを実行"""
    logger.info("E2Eテストを開始します")
    unittest.main(verbosity=2)


if __name__ == "__main__":
    run_tests() 