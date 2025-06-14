from PIL import Image
from PyQt6.QtGui import QImage, QPixmap
import pickle
import os
from pathlib import Path

# 画像拡張子リスト
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp"}

def filter_corrupt_images(image_paths):
    """
    画像パスリストから破損画像を除外し、(正常画像リスト, 破損画像リスト)を返す
    """
    valid, corrupt = [], []
    for img in image_paths:
        pil_ok = True
        qt_ok = True
        # PILチェック
        try:
            with Image.open(img) as im:
                im.verify()
        except Exception:
            pil_ok = False
        # Qtチェック
        qimg = QImage(img)
        if qimg.isNull():
            qt_ok = False
        if pil_ok and qt_ok:
            valid.append(img)
        else:
            corrupt.append(img)
    return valid, corrupt 

def find_warn_images(image_paths):
    """
    警告画像を検出（全データのロードによる厳密チェック）
    
    QPixmapとPillowの両方でチェックを行い、どちらかで失敗した画像を検出します。
    qt.gui.imageio.jpeg: Corrupt JPEGの警告が出る画像を検出することも目的としています。
    """
    warn = []
    for img in image_paths:
        try:
            # 1. QPixmapでチェック（これが実際にUIで使われる）
            qpixmap = QPixmap(img)
            if qpixmap.isNull() or qpixmap.width() == 0 or qpixmap.height() == 0:
                warn.append(img)
                # print(f"警告画像検出(QPixmap): {img}")  # 詳細ログ抑制
                continue
                
            # 2. Pillowで完全に読み込み可能か確認
            with Image.open(img) as im:
                im.load()  # 全データをロード
        except Exception as e:
            warn.append(img)
            # print(f"警告画像検出(例外): {img} ({e})")  # 詳細ログ抑制
            continue
            
    return warn

def resave_jpeg(src_path, dst_path=None):
    """
    画像を再保存して修復を試みる
    """
    if dst_path is None:
        base, ext = os.path.splitext(src_path)
        dst_path = f"{base}_fixed{ext}"
    try:
        with Image.open(src_path) as im:
            im = im.convert('RGB')
            im.save(dst_path, 'JPEG', quality=95)
        print(f"✔️ 修正保存: {dst_path}")
        return dst_path
    except Exception as e:
        print(f"❌ エラー: {src_path} ({e})")
        return None

def check_and_fix_cache(cache, save_fixed=True, cache_file="detect_cache.pkl"):
    """
    キャッシュを検査し、警告画像を修正または除外する統一関数
    
    Args:
        cache (dict): キャッシュデータ（detect_cache.pkl）
        save_fixed (bool): 修正キャッシュを保存するかどうか
        cache_file (str): キャッシュファイルのパス
        
    Returns:
        tuple: (修正済みキャッシュ, パス変換マップ, 除外画像リスト)
    """
    print(f"キャッシュ検査開始: {len(cache)}件")
    # 画像パスを抽出
    image_paths = list(set([k[2] for k in cache.keys()]))
    print(f"画像数: {len(image_paths)}")
    
    # --- 警告画像の自動修正・キャッシュ修正 ---
    warn_imgs = find_warn_images(image_paths)
    print(f"警告画像数: {len(warn_imgs)}")
    if warn_imgs:
        print("警告画像リスト:")
        for p in warn_imgs:
            print(p)
    
    path_map = {}
    exclude_imgs = set()
    for img_path in warn_imgs:
        fixed_path = resave_jpeg(img_path)
        if fixed_path:
            path_map[img_path] = fixed_path
        else:
            exclude_imgs.add(img_path)
    
    if exclude_imgs:
        print("リペアできず除外した画像:")
        for p in exclude_imgs:
            print(p)
    
    new_cache = {}
    for k, v in cache.items():
        model_path, label_id, img_path = k
        if img_path in exclude_imgs:
            continue  # リペアできなかった画像は除外
        if img_path in path_map:
            new_key = (model_path, label_id, path_map[img_path])
            new_cache[new_key] = v
        else:
            new_cache[k] = v
    
    print(f"検査後キャッシュ件数: {len(new_cache)}")
    # --- チェック済みフラグ付きで保存 ---
    cache_wrapper = {"is_checked": True, "data": new_cache}
    if save_fixed and cache_file:
        with open(cache_file, "wb") as f:
            pickle.dump(cache_wrapper, f)
        print(f"キャッシュを {cache_file} に保存しました (is_checked=True)")
    
    return new_cache, path_map, exclude_imgs

def scan_folder_for_valid_images(folder_path):
    """
    フォルダをスキャンして有効な画像リストを返す（破損画像を除外）
    Args:
        folder_path (str): スキャンするフォルダのパス
    Returns:
        list: 有効な画像のパスリスト
    """
    image_files = []
    corrupt_files = []
    
    folder = Path(folder_path)
    for root, _, files in os.walk(folder):
        for file in files:
            file_path = Path(root) / file
            if file_path.suffix.lower() in IMAGE_EXTENSIONS:
                # 破損チェック
                try:
                    # QPixmapで正常に読めるかチェック
                    pixmap = QPixmap(str(file_path))
                    if pixmap.isNull() or pixmap.width() == 0 or pixmap.height() == 0:
                        corrupt_files.append(str(file_path))
                        # print(f"[除外] 破損画像(QPixmap): {file_path}")  # 詳細ログ抑制
                        continue
                    # 念のためPILでも確認
                    with Image.open(str(file_path)) as im:
                        im.verify()
                    # 正常な画像として追加
                    image_files.append(str(file_path))
                except Exception as e:
                    corrupt_files.append(str(file_path))
                    # print(f"[除外] 破損画像(PIL): {file_path} ({e})")  # 詳細ログ抑制
    # if corrupt_files:
    #     print(f"{len(corrupt_files)}件の破損画像をスキップしました")  # 詳細ログ抑制
    # print(f"[INFO] サムネイル化対象画像: {image_files}")  # 詳細ログ抑制
    return image_files