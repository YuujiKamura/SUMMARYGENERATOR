import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
import json
from PIL import Image
from glob import glob
import tempfile
import shutil
import hashlib
from ocr_config_loader import load_documentai_config
from documentai_engine import DocumentAIOCREngine
# from ocr_aa_layout import print_ocr_aa_layout
from google.protobuf.json_format import MessageToDict
from google.cloud.documentai_v1.types import Document

# パスマネージャを使用してリソースパス解決
try:
    from utils.path_manager import PathManager
    path_manager = PathManager()
    CACHE_DIR = str(path_manager.src_dir / 'image_preview_cache')
    # summarygeneratorプロジェクトではocr_tools内にpreset_rolesを配置
    PRESET_ROLES_PATH = os.path.join(os.path.dirname(__file__), 'preset_roles.json')
    # DocumentAI設定ファイルもocr_tools/credential内に配置
    DOCUMENTAI_CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'credential', 'documentai_config.json')
    # OCRキャッシュとクレデンシャルをocr_tools内に配置
    OCR_CACHE_DIR = os.path.join(os.path.dirname(__file__), 'ocr_cache')
    CREDENTIAL_PATH = os.path.join(os.path.dirname(__file__), 'credential', 'visionapi-437405-0cd91b6d2db4.json')
    print(f"[INFO] PathManager使用: {path_manager.project_root}")
except ImportError as e:
    print(f"[WARN] PathManagerのインポートに失敗: {e}")
    # フォールバック: 従来のパス解決方法
    CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'src', 'image_preview_cache')
    PRESET_ROLES_PATH = os.path.join(os.path.dirname(__file__), 'preset_roles.json')
    # DocumentAI設定ファイルもocr_tools/credential内に配置
    DOCUMENTAI_CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'credential', 'documentai_config.json')
    OCR_CACHE_DIR = os.path.join(os.path.dirname(__file__), 'ocr_cache')
    CREDENTIAL_PATH = os.path.join(os.path.dirname(__file__), 'credential', 'visionapi-437405-0cd91b6d2db4.json')
os.makedirs(OCR_CACHE_DIR, exist_ok=True)

# デバッグ用：設定されたパスを表示
print(f"[DEBUG] OCR_CACHE_DIR: {OCR_CACHE_DIR}")
print(f"[DEBUG] CACHE_DIR: {CACHE_DIR}")
print(f"[DEBUG] PRESET_ROLES_PATH: {PRESET_ROLES_PATH}")
print(f"[DEBUG] DOCUMENTAI_CONFIG_PATH: {DOCUMENTAI_CONFIG_PATH}")
print(f"[DEBUG] CREDENTIAL_PATH: {CREDENTIAL_PATH}")

MIN_BBOX_RATIO = 0.5

def load_preset_labels_and_roles(preset_roles_path):
    with open(preset_roles_path, encoding='utf-8') as f:
        data = json.load(f)
    labels = set()
    for entry in data:
        if 'label' in entry:
            labels.add(entry['label'])
    return labels

def bbox_area(xyxy):
    x1, y1, x2, y2 = xyxy
    return max(0, x2 - x1) * max(0, y2 - y1)

def copy_to_local(img_path):
    """
    画像を一時ローカルにコピーし、そのパスを返す。既にコピー済みなら再利用。
    """
    tmp_dir = tempfile.gettempdir()
    file_hash = hashlib.md5(img_path.encode()).hexdigest()[:8]
    basename = os.path.basename(img_path)
    temp_path = os.path.join(tmp_dir, f"{file_hash}_{basename}")
    if os.path.exists(temp_path):
        return temp_path
    try:
        shutil.copy2(img_path, temp_path)
        return temp_path
    except Exception as e:
        print(f"[WARN] 画像一時コピー失敗: {img_path}: {e}")
        return None

def get_image_size_local(image_path):
    """
    画像を一時ローカルにコピーしてからサイズを取得
    """
    local_path = copy_to_local(image_path)
    if not local_path or not os.path.exists(local_path):
        raise FileNotFoundError(f"ローカルコピー失敗: {image_path}")
    with Image.open(local_path) as img:
        return img.width, img.height, local_path

def init_documentai_engine():
    conf = load_documentai_config(DOCUMENTAI_CONFIG_PATH)
    project_id = conf.get('project_id', '')
    location = conf.get('location', '')
    processor_id = conf.get('processor_id', '')
    credential_path = conf.get('credential_path', '') or conf.get('credentials_path', '')
    return DocumentAIOCREngine(
        project_id=project_id,
        location=location,
        processor_id=processor_id,
        credentials_path=credential_path
    )

def get_text_from_layout(document, layout):
    """DocumentAIのlayoutからテキストを抽出"""
    if not hasattr(layout, 'text_anchor') or not layout.text_anchor:
        return ""
    if not hasattr(document, 'text') or not document.text:
        return ""
    # text_anchor.text_segments から範囲を取得
    text = ""
    for segment in layout.text_anchor.text_segments:
        start = int(segment.start_index) if segment.start_index else 0
        end = int(segment.end_index) if segment.end_index else 0
        text += document.text[start:end]
    return text

def extract_texts_with_boxes_from_documentai_result(document, image_width, image_height):
    """
    DocumentAIのdocumentオブジェクトからテキスト＋左上座標リストを抽出（paragraphs単位、normalized_vertices優先）
    """
    results = []
    if not hasattr(document, 'pages'):
        return results
    for page in document.pages:
        for para in getattr(page, 'paragraphs', []):
            if not (hasattr(para, 'layout') and hasattr(para.layout, 'bounding_poly') and para.layout.bounding_poly):
                continue
            text = get_text_from_layout(document, para.layout)
            # normalized_vertices優先
            vertices = []
            if hasattr(para.layout.bounding_poly, 'normalized_vertices') and para.layout.bounding_poly.normalized_vertices:
                v = para.layout.bounding_poly.normalized_vertices[0]
                x = int((v.x or 0) * image_width)
                y = int((v.y or 0) * image_height)
                if text:
                    results.append({'text': text, 'x': x, 'y': y})
            elif hasattr(para.layout.bounding_poly, 'vertices') and para.layout.bounding_poly.vertices:
                v = para.layout.bounding_poly.vertices[0]
                x = int(v.x or 0)
                y = int(v.y or 0)
                if text:
                    results.append({'text': text, 'x': x, 'y': y})
        # --- 既存のwords抽出はコメントアウトで残す ---
        # for block in getattr(page, 'blocks', []):
        #     for paragraph in getattr(block, 'paragraphs', []):
        #         for word in getattr(paragraph, 'words', []):
        #             text = ''.join([s.text for s in getattr(word, 'symbols', []) if hasattr(s, 'text')])
        #             if not text:
        #                 continue
        #             if hasattr(word, 'layout') and hasattr(word.layout, 'bounding_poly'):
        #                 vertices = word.layout.bounding_poly.vertices
        #                 if vertices and len(vertices) > 0:
        #                     x = int(vertices[0].x or 0)
        #                     y = int(vertices[0].y or 0)
        #                     x = min(max(x, 0), image_width-1)
        #                     y = min(max(y, 0), image_height-1)
        #                     results.append({'text': text, 'x': x, 'y': y})
    return results

def get_cache_path(image_path):
    h = hashlib.md5(image_path.encode('utf-8')).hexdigest()
    cache_file = f"{h}.json"
    cache_path = os.path.join(OCR_CACHE_DIR, cache_file)
    print(f"[DEBUG] 生成されたハッシュ: {h}")
    print(f"[DEBUG] キャッシュファイル名: {cache_file}")
    return cache_path

def load_ocr_cache(image_path):
    cache_path = get_cache_path(image_path)
    print(f"[DEBUG] キャッシュパス検索: {cache_path}")
    print(f"[DEBUG] 元画像パス: {image_path}")
    if os.path.exists(cache_path):
        print(f"[DEBUG] キャッシュファイル見つかりました")
        with open(cache_path, encoding='utf-8') as f:
            return json.load(f)
    else:
        print(f"[DEBUG] キャッシュファイルが存在しません")
    return None

def save_ocr_cache(image_path, ocr_result):
    cache_path = get_cache_path(image_path)
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(ocr_result, f, ensure_ascii=False, indent=2)

def process_image_json(json_path, preset_roles_path, documentai_engine, min_bbox_ratio=MIN_BBOX_RATIO):
    """
    1件のimage_preview_cacheのjsonを処理し、OCR結果とAA配置をprintする
    """
    labels = load_preset_labels_and_roles(preset_roles_path)
    with open(json_path, encoding='utf-8') as f:
        data = json.load(f)
    image_path = data.get('image_path')
    if not image_path:
        print(f"[SKIP] image_pathなし: {json_path}")
        return
    try:
        img_w, img_h, local_path = get_image_size_local(image_path)
    except Exception as e:
        print(f"[WARN] 画像サイズ取得失敗: {image_path}: {e}")
        return
    found = False
    for bbox in data.get('bboxes', []):
        label = bbox.get('cname')
        role = bbox.get('role')
        xyxy = bbox.get('xyxy')
        if not xyxy:
            continue
        area = bbox_area(xyxy)
        img_area = img_w * img_h
        ratio = area / img_area if img_area > 0 else 0
        if (label in labels or role in labels) and ratio >= min_bbox_ratio:
            found = True
            print(f"対象画像: {image_path} (bbox ratio={ratio:.2f})")
            # キャッシュ確認
            cache = load_ocr_cache(local_path)
            if cache is not None:
                print("[CACHE] OCR結果を再利用 (キャッシュヒット)")
                document = Document.from_json(json.dumps(cache['document']))
            else:
                print("[CACHE] OCR結果を新規取得 (キャッシュミス)")
                # OCR実行
                result = documentai_engine.client.process_document(request={
                    "name": documentai_engine.processor_name,
                    "raw_document": {"content": open(local_path, "rb").read(), "mime_type": "image/jpeg"}
                })
                document = result.document
                # キャッシュ保存
                save_ocr_cache(local_path, {"document": MessageToDict(document._pb)})
            text = document.text if hasattr(document, 'text') else ''
            # print(f"OCR結果:\n{text}\n{'-'*40}")  # ←この行を削除
            texts_with_boxes = extract_texts_with_boxes_from_documentai_result(document, img_w, img_h)
            print("[DEBUG] texts_with_boxes:", texts_with_boxes)
            # print_ocr_aa_layout(texts_with_boxes, img_w, img_h)
            break
    if not found:
        print(f"[SKIP] 条件に合致するbboxなし: {json_path}")

def main():
    labels = load_preset_labels_and_roles(PRESET_ROLES_PATH)
    engine = init_documentai_engine()
    json_files = glob(os.path.join(CACHE_DIR, '*.json'))
    # 条件に合致した画像のローカルパスリストを作成
    target_local_paths = []
    target_image_paths = []
    for jf in json_files:
        with open(jf, encoding='utf-8') as f:
            data = json.load(f)
        image_path = data.get('image_path')
        if not image_path:
            continue
        try:
            img_w, img_h, local_path = get_image_size_local(image_path)
        except Exception as e:
            print(f"[WARN] 画像サイズ取得失敗: {image_path}: {e}")
            continue
        for bbox in data.get('bboxes', []):
            label = bbox.get('cname')
            role = bbox.get('role')
            xyxy = bbox.get('xyxy')
            if not xyxy:
                continue
            area = bbox_area(xyxy)
            img_area = img_w * img_h
            ratio = area / img_area if img_area > 0 else 0
            if (label in labels or role in labels) and ratio >= MIN_BBOX_RATIO:
                target_local_paths.append(local_path)
                target_image_paths.append(image_path)
                break
    # 2枚ずつ連結してOCR
    for i in range(0, len(target_local_paths), 2):
        imgs = target_local_paths[i:i+2]
        origs = target_image_paths[i:i+2]
        if len(imgs) == 1:
            concat_path = imgs[0]
            with Image.open(concat_path) as img:
                concat_w, concat_h = img.width, img.height
        else:
            try:
                img1 = Image.open(imgs[0])
                img2 = Image.open(imgs[1])
                total_width = img1.width + img2.width
                max_height = max(img1.height, img2.height)
                new_img = Image.new('RGB', (total_width, max_height), (255,255,255))
                new_img.paste(img1, (0, 0))
                new_img.paste(img2, (img1.width, 0))
                tmp_dir = tempfile.gettempdir()
                concat_path = os.path.join(tmp_dir, f"concat_{i}_{os.path.basename(imgs[0])}_{os.path.basename(imgs[1])}")
                new_img.save(concat_path, 'JPEG')
                concat_w, concat_h = total_width, max_height
            except Exception as e:
                print(f"[WARN] 画像連結失敗: {imgs}: {e}")
                continue
        print(f"連結画像: {origs} -> {concat_path}")
        # OCR実行
        result = engine.client.process_document(request={
            "name": engine.processor_name,
            "raw_document": {"content": open(concat_path, "rb").read(), "mime_type": "image/jpeg"}
        })
        document = result.document
        text = document.text if hasattr(document, 'text') else ''
        # print(f"OCR結果:\n{text}\n{'-'*40}")  # ←この行を削除
        texts_with_boxes = extract_texts_with_boxes_from_documentai_result(document, concat_w, concat_h)
        print("[DEBUG] texts_with_boxes:", texts_with_boxes)
        # print_ocr_aa_layout(texts_with_boxes, concat_w, concat_h)
    # # 1枚ずつ処理（従来）
    # for local_path, image_path in zip(target_local_paths, target_image_paths):
    #     print(f"対象画像: {image_path}")
    #     text = engine.extract_text(local_path)
    #     print(f"OCR結果:\n{text}\n{'-'*40}")

if __name__ == '__main__':
    main()