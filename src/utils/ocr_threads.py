#!/usr/bin/env python3
"""
OCR処理用のスレッドクラス
"""
import os
import json
import tempfile
import shutil
import io
from PyQt6.QtCore import QThread, pyqtSignal
from PIL import Image

# Google Cloud Vision APIのクライアントライブラリ
from google.cloud import vision
from google.oauth2 import service_account


# Vision API OCR処理用のスレッドクラス
class VisionApiOcrThread(QThread):
    """Vision APIでのOCR処理を行うスレッドクラス"""
    progress_updated = pyqtSignal(int, int)  # 現在の進捗、全体数
    result_ready = pyqtSignal(dict)  # OCR結果
    processing_file = pyqtSignal(str)  # 処理中のファイル名
    finished_signal = pyqtSignal(bool)  # 処理完了シグナル(成功/失敗)
    
    def __init__(self, image_paths, detection_results, credential_path, parent=None):
        super().__init__(parent)
        self.image_paths = image_paths
        self.detection_results = detection_results
        self.credential_path = credential_path
        self.running = True
        self.ocr_results = {}
        self.temp_dir = None
    
    def run(self):
        """スレッド実行処理"""
        try:
            # 一時ディレクトリを作成
            self.temp_dir = tempfile.mkdtemp(prefix="vision_api_ocr_")
            
            # 既存のOCR結果をロード
            ocr_cache_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "ocr_results_cache.json")
            cached_results = {}
            if os.path.exists(ocr_cache_file):
                try:
                    with open(ocr_cache_file, 'r', encoding='utf-8') as f:
                        cached_results = json.load(f)
                except Exception as e:
                    print(f"OCRキャッシュ読み込みエラー: {e}")
            
            # Vision APIクライアントの初期化
            credentials = service_account.Credentials.from_service_account_file(self.credential_path)
            client = vision.ImageAnnotatorClient(credentials=credentials)
            
            total = len(self.image_paths)
            for i, image_path in enumerate(self.image_paths, 1):
                if not self.running:
                    break
                
                if not os.path.exists(image_path):
                    continue
                
                self.processing_file.emit(os.path.basename(image_path))
                self.progress_updated.emit(i, total)
                
                # キャッシュにある場合はそれを使用
                if image_path in cached_results:
                    print(f"キャッシュから読み込み: {image_path}")
                    self.ocr_results[image_path] = cached_results[image_path]
                    continue
                
                # 検出結果からバウンディングボックスを取得
                detections = self.detection_results.get(image_path, [])
                if not detections:
                    continue
                
                # 画像ごとの結果辞書
                image_results = {
                    "path": image_path,
                    "detections": []
                }
                
                # 各検出に対してOCR処理
                for j, detection in enumerate(detections):
                    if "bbox" not in detection:
                        continue
                    
                    # バウンディングボックスから画像をクリッピング
                    cropped_path = self._crop_image(image_path, detection["bbox"], j)
                    if not cropped_path:
                        continue
                    
                    # Vision APIで文字認識
                    ocr_text = self._detect_text(client, cropped_path)
                    
                    # 結果を保存
                    detection_result = {
                        "class": detection.get("class_name", str(detection.get("class", ""))),
                        "confidence": detection.get("confidence", 0),
                        "bbox": detection["bbox"],
                        "ocr_text": ocr_text
                    }
                    image_results["detections"].append(detection_result)
                
                self.ocr_results[image_path] = image_results
                # キャッシュに追加
                cached_results[image_path] = image_results
            
            # キャッシュを保存
            os.makedirs(os.path.dirname(ocr_cache_file), exist_ok=True)
            with open(ocr_cache_file, 'w', encoding='utf-8') as f:
                json.dump(cached_results, f, ensure_ascii=False, indent=2)
            
            # 結果を送信
            self.result_ready.emit(self.ocr_results)
            self.finished_signal.emit(True)
        
        except Exception as e:
            print(f"Vision API OCR処理エラー: {e}")
            self.finished_signal.emit(False)
        
        finally:
            # 一時ディレクトリを削除
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
    
    def _crop_image(self, image_path, bbox, index):
        """バウンディングボックスに基づいて画像をクリッピング"""
        try:
            img = Image.open(image_path)
            width, height = img.size
            
            # バウンディングボックスの取得 (x1, y1, x2, y2)
            x1, y1, x2, y2 = bbox
            
            # 相対座標から絶対座標に変換
            abs_x1 = int(x1 * width)
            abs_y1 = int(y1 * height)
            abs_x2 = int(x2 * width)
            abs_y2 = int(y2 * height)
            
            # 画像のクリッピング
            cropped_img = img.crop((abs_x1, abs_y1, abs_x2, abs_y2))
            
            # 一時ファイルに保存
            img_basename = os.path.basename(image_path)
            crop_filename = f"{os.path.splitext(img_basename)[0]}_crop_{index}.jpg"
            crop_path = os.path.join(self.temp_dir, crop_filename)
            
            cropped_img.save(crop_path)
            return crop_path
        
        except Exception as e:
            print(f"画像クリッピングエラー: {e}")
            return None
    
    def _detect_text(self, client, image_path):
        """Vision APIを使用して文字検出"""
        try:
            with io.open(image_path, 'rb') as image_file:
                content = image_file.read()
            
            image = vision.Image(content=content)
            response = client.text_detection(image=image)
            
            if response.error.message:
                print(f"API エラー: {response.error.message}")
                return ""
            
            texts = response.text_annotations
            if texts:
                # 最初のテキスト検出は全体のテキスト
                return texts[0].description
            
            return ""
        
        except Exception as e:
            print(f"Vision API エラー: {e}")
            return ""
    
    def stop(self):
        """スレッドの停止"""
        self.running = False 