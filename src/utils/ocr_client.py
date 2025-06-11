#!/usr/bin/env python3
"""
PaddleOCRを使用したOCRクライアント
"""
import os
import time
import threading
import warnings
from typing import List, Dict, Any, Optional
import numpy as np
from pathlib import Path

# プロジェクトルートからの相対パスでキャッシュディレクトリを設定
project_root = Path(__file__).parent.parent.parent
cache_dir = project_root / "models" / "paddle_ocr_cache"
os.makedirs(cache_dir, exist_ok=True)
os.environ["PADDLE_OCR_HOME"] = str(cache_dir)

# PaddleOCRに依存するケースと、それ以外のケースの両方に対応
PADDLEOCR_AVAILABLE = False
try:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from paddleocr import PaddleOCR
        # 実際にインポートできるか試す
        test = PaddleOCR  
        PADDLEOCR_AVAILABLE = True
except (ImportError, OSError) as e:
    print(f"PaddleOCRのロードエラー: {e}")
    print("モック実装を使用します。")

# グローバルシングルトンインスタンス
_OCR_CLIENT = None
_LOCK = threading.Lock()

# モック実装（PaddleOCRが利用できない場合）
class MockOCR:
    """PaddleOCRのモック実装"""
    def __init__(self, **kwargs):
        self.lang = kwargs.get('lang', 'japan')
        self.use_gpu = kwargs.get('use_gpu', False)
        print(f"MockOCR初期化: lang={self.lang}, use_gpu={self.use_gpu}")
        
    def ocr(self, image, **kwargs):
        """OCRのモック実装"""
        height, width = image.shape[:2] if hasattr(image, 'shape') else (100, 100)
        
        # 言語に応じたダミーテキスト
        if self.lang == 'japan':
            text = 'テストテキスト'
        elif self.lang == 'en':
            text = 'Test Text'
        else:
            text = 'Sample Text'
            
        # ダミーのOCR結果を返す
        result = [[[(10, 10), (text, 0.98)]]]
        print(f"MockOCR実行: サイズ {width}x{height}, テキスト '{text}'")
        return result

def get_ocr_client(lang="japan", use_gpu=False):
    """シングルトンOCRクライアントを取得"""
    global _OCR_CLIENT
    
    with _LOCK:
        if _OCR_CLIENT is None:
            if PADDLEOCR_AVAILABLE:
                try:
                    start = time.time()
                    print(f"PaddleOCRモデルをロード中... (言語: {lang}, GPU: {use_gpu})")
                    _OCR_CLIENT = PaddleOCR(
                        use_gpu=use_gpu,
                        lang=lang,
                        det=False,  # 既に切り出すので検出は不要
                        rec=True,
                        cls=False,
                        show_log=False
                    )
                    print(f"PaddleOCRロード完了: {time.time() - start:.1f}秒")
                except Exception as e:
                    print(f"PaddleOCR初期化中にエラーが発生: {e}, モック実装に切り替えます")
                    _OCR_CLIENT = MockOCR(lang=lang, use_gpu=use_gpu)
            else:
                # PaddleOCRが利用できない場合はモック実装を使用
                _OCR_CLIENT = MockOCR(lang=lang, use_gpu=use_gpu)
    
    return _OCR_CLIENT

def extract_texts_from_clips(
    img_path: str,
    detections: List[Dict[str, Any]],
    lang: str = "japan",
    use_gpu: bool = False,
    contrast: float = 2.0,
) -> Dict[int, List[str]]:
    """画像と検出ボックスからテキストを抽出"""
    from PIL import Image, ImageEnhance
    
    # 画像ファイルの存在確認
    if not Path(img_path).exists():
        print(f"エラー: 画像ファイルが見つかりません: {img_path}")
        return {}
    
    try:
        # OCRクライアント取得（一度ロードしたらメモリに保持）
        ocr = get_ocr_client(lang, use_gpu)
        
        # 画像読み込みと前処理
        img = Image.open(img_path).convert("L")
        img = ImageEnhance.Contrast(img).enhance(contrast)
        img_rgb = img.convert("RGB")
        
        results = {}
        
        for idx, det in enumerate(detections):
            xy = det.get("xyxy")
            if not xy or len(xy) != 4:
                results[idx] = []
                continue
            
            # 領域切り出し
            x1, y1, x2, y2 = map(int, xy)
            clip = img_rgb.crop((x1, y1, x2, y2))
            clip_np = np.asarray(clip)
            
            # OCR実行
            ocr_result = ocr.ocr(clip_np, det=False, rec=True, cls=False)
            
            # 結果解析
            texts = []
            if ocr_result and len(ocr_result) > 0 and ocr_result[0]:
                texts = [item[1][0] for item in ocr_result[0]]
            
            results[idx] = texts
        
        return results
    except Exception as e:
        print(f"OCR処理中にエラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        return {idx: [f"エラー: {str(e)}"] for idx in range(len(detections))}

# アプリ起動時にバックグラウンドでモデルをプリロード
def preload_ocr_model(lang="japan", use_gpu=False):
    """アプリ起動時に別スレッドでOCRモデルを事前ロード"""
    def _load_in_background():
        try:
            get_ocr_client(lang, use_gpu)
            print("OCRモデルのプリロードが完了しました。")
        except Exception as e:
            print(f"OCRモデルのプリロード中にエラーが発生しました: {e}")
    
    thread = threading.Thread(target=_load_in_background)
    thread.daemon = True
    thread.start()
    return thread

# 単体テスト用
if __name__ == "__main__":
    print(f"OCRクライアントモジュールのテスト")
    print(f"PaddleOCR利用可能: {PADDLEOCR_AVAILABLE}")
    print(f"キャッシュディレクトリ: {cache_dir}")
    
    # テスト用の小さな画像を作成
    from PIL import Image, ImageDraw, ImageFont
    test_dir = project_root / "test_images"
    os.makedirs(test_dir, exist_ok=True)
    test_img_path = test_dir / "ocr_test.png"
    
    if not test_img_path.exists():
        print(f"テスト画像を作成: {test_img_path}")
        img = Image.new('RGB', (200, 100), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), 'テストABC123', fill=(0, 0, 0))
        img.save(test_img_path)
    
    # テスト実行
    test_detections = [
        {
            "class": 0,
            "class_name": "text",
            "confidence": 0.85,
            "xyxy": [0, 0, 200, 100]
        }
    ]
    
    print("\nOCR実行中...")
    results = extract_texts_from_clips(str(test_img_path), test_detections)
    print("OCR結果:")
    for idx, texts in results.items():
        print(f"領域 {idx}: {texts}")
    
    print("\nOCRクライアント再利用テスト")
    client1 = get_ocr_client()
    client2 = get_ocr_client()
    print(f"同一インスタンス: {client1 is client2}")
    
    print("\nテスト完了") 