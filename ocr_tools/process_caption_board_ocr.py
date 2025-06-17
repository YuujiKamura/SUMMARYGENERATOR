import os
import sys
from datetime import datetime
from typing import List, Optional

# --- パス設定と基本インポート ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
src_dir = os.path.join(project_root, 'src')

# packageルートを優先的に追加
if project_root not in sys.path: sys.path.insert(0, project_root)
if current_dir not in sys.path: sys.path.insert(0, current_dir)
if src_dir not in sys.path: sys.path.insert(0, src_dir)

# --- 外部モジュール ---
from caption_board_ocr_pipeline import process_caption_board_image
from ocr_tools.caption_board_ocr_reporter import (
    print_extracted_results_summary,
    save_success_results,
    get_final_location_list,
)
from caption_board_ocr_data import load_image_cache_master, find_caption_board_images
from exif_utils import get_capture_time_with_fallback, extract_image_number
from survey_point import SurveyPoint
from ocr_value_extractor import init_documentai_engine
from src.utils.image_entry import ImageEntry, ImageEntryList

# --- パラメータ ---
TIME_WINDOW_SEC = 300  # 5分以内を隣接とみなす

class CaptionBoardOCRPipeline:
    """キャプションボードOCR処理を担当するパイプライン"""
    
    def __init__(self, project_root: str, src_dir: str):
        self.project_root = project_root
        self.src_dir = src_dir
        self.engine = None
        
    def initialize_engine(self):
        """DocumentAIエンジンを初期化"""
        try:
            self.engine = init_documentai_engine()
            return True
        except Exception as e:
            print(f"DocumentAI エンジンの初期化に失敗: {e}")
            return False
    
    def process_image_entry(self, image_entry: ImageEntry) -> ImageEntry:
        """ImageEntryに対してOCR処理を実行し、SurveyPointを設定"""
        if not self.engine:
            print("エンジンが初期化されていません")
            return image_entry
            
        # キャプションボード画像かチェック
        if not self._has_caption_board_bbox(image_entry):
            # 非キャプションボード画像の場合、基本的なSurveyPointを作成
            survey_point = self._create_basic_survey_point(image_entry)
            image_entry.survey_point = survey_point
            return image_entry
            
        # キャプションボードOCR処理実行
        ocr_data = self._extract_caption_board_data(image_entry)
        if ocr_data:
            # OCR結果からSurveyPointを生成
            survey_point = SurveyPoint.from_raw(ocr_data)
            image_entry.survey_point = survey_point
        else:
            # OCR失敗時は基本的なSurveyPointを作成
            survey_point = self._create_basic_survey_point(image_entry)
            image_entry.survey_point = survey_point
            
        return image_entry
    
    def _has_caption_board_bbox(self, image_entry: ImageEntry) -> bool:
        """ImageEntryがキャプションボードのbboxを持っているかチェック"""
        # まずキャッシュJSONが読み込まれていない場合は読み込む
        if not image_entry.cache_json:
            image_entry.load_cache_json()
        
        return image_entry.has_caption_board_bbox()
    
    def _extract_caption_board_data(self, image_entry: ImageEntry) -> Optional[dict]:
        """キャプションボードからOCRデータを抽出"""
        if not image_entry.image_path:
            return None
        
        # キャッシュJSONが読み込まれていない場合は読み込む
        if not image_entry.cache_json:
            image_entry.load_cache_json()
            
        # キャプションボードのbboxを取得
        caption_board_bbox = image_entry.get_caption_board_bbox()
        if not caption_board_bbox:
            return None
            
        try:
            # OCRパイプライン用の画像情報を構築
            img_info = {
                'filename': os.path.basename(image_entry.image_path),
                'image_path': image_entry.image_path,
                'bbox': caption_board_bbox
            }
            
            # OCR処理実行
            raw_ocr_data = process_caption_board_image(
                img_info, self.engine, self.project_root, self.src_dir
            )
            
            if raw_ocr_data:
                # capture_timeを追加
                capture_time = get_capture_time_with_fallback(image_entry.image_path)
                if capture_time is None:
                    try:
                        capture_time = os.path.getmtime(image_entry.image_path)
                    except:
                        pass
                raw_ocr_data['capture_time'] = capture_time
                
            return raw_ocr_data
            
        except Exception as e:
            print(f"OCR処理エラー: {e}")
            return None
    
    def _create_basic_survey_point(self, image_entry: ImageEntry) -> SurveyPoint:
        """基本的なSurveyPointを作成（OCR処理なし）"""
        if not image_entry.image_path:
            return SurveyPoint()
            
        capture_time = get_capture_time_with_fallback(image_entry.image_path)
        if capture_time is None:
            try:
                capture_time = os.path.getmtime(image_entry.image_path)
            except:
                pass
                
        sp = SurveyPoint(
            capture_time=capture_time
        )
        sp.filename = os.path.basename(image_entry.image_path)
        sp.image_path = image_entry.image_path
        return sp

def _load_image_entries(target_filename=None) -> ImageEntryList:
    """全画像データからImageEntryListを作成する"""
    # データ準備
    all_image_data = load_image_cache_master(project_root)
    if not all_image_data:
        print("画像データが見つかりません。")
        return ImageEntryList()
    
    # 単一画像指定の場合はフィルタリング
    if target_filename:
        all_image_data = [item for item in all_image_data if os.path.basename(item['image_path']) == target_filename]
        if not all_image_data:
            print(f"❌ {target_filename} が見つかりません")
            return ImageEntryList()
    
    # print(f"総画像数: {len(all_image_data)}件")
    
    # ImageEntryリスト作成
    entries = []
    for item in sorted(all_image_data, key=lambda x: extract_image_number(x['image_path'])):
        entry = ImageEntry(
            image_path=item['image_path'],
            cache_json=item  # 旧データとして保持
        )
        # SHAハッシュベースのキャッシュJSONを読み込み
        entry.load_cache_json()
        entries.append(entry)
    
    return ImageEntryList(entries=entries, group_type='caption_board_images')

def _supplement_survey_points(image_entries: ImageEntryList) -> List[dict]:
    """SurveyPointの補完処理を実行し、最終結果のdictリストを返す"""
    entries = image_entries.entries
    
    # 全エントリを対象とし、image_pathがあるエントリのみを抽出
    valid_entries = [entry for entry in entries if entry.image_path is not None]
    
    if not valid_entries:
        return []
    
    print(f"DEBUG: 有効エントリ数: {len(valid_entries)}")
    
    # capture_timeでソート（SurveyPointがない場合はファイル更新時刻を使用）
    sorted_entries = sorted(
        valid_entries, 
        key=lambda x: (
            extract_image_number(x.image_path) if x.image_path else 0
        )
    )
    
    print(f"DEBUG: ソート後エントリ数: {len(sorted_entries)}")
    
    # 補完処理
    final_results = []
    for i, entry in enumerate(sorted_entries):
        current_sp = entry.survey_point
        
        # SurveyPointがない場合は前後から補完を試行
        if current_sp is None:
            # 基本的なSurveyPointを作成
            from survey_point import SurveyPoint
            if entry.image_path:  # image_pathがNoneでないことを確認
                capture_time = get_capture_time_with_fallback(entry.image_path)
                if capture_time is None:
                    try:
                        capture_time = os.path.getmtime(entry.image_path)
                    except:
                        pass
                        
                current_sp = SurveyPoint(
                    capture_time=capture_time
                )
                current_sp.filename = os.path.basename(entry.image_path)
                current_sp.image_path = entry.image_path
            else:
                continue  # image_pathがNoneの場合はスキップ
                
        # 前後のSurveyPointを取得
        prev_sp = None
        next_sp = None
        
        # 前方向の有効なSurveyPointを探す
        for j in range(i-1, -1, -1):
            if sorted_entries[j].survey_point is not None:
                prev_sp = sorted_entries[j].survey_point
                break
                
        # 後方向の有効なSurveyPointを探す
        for j in range(i+1, len(sorted_entries)):
            if sorted_entries[j].survey_point is not None:
                next_sp = sorted_entries[j].survey_point
                break
        
        # デバッグ出力：前後のSurveyPoint情報
        current_filename = os.path.basename(entry.image_path) if entry.image_path else 'None'
        prev_location = prev_sp.get('location') if prev_sp else None
        next_location = next_sp.get('location') if next_sp else None
        current_location = current_sp.get('location') if current_sp else None
        
        if current_filename == "RIMG8586.JPG":
            print(f"DEBUG: RIMG8586補完詳細:")
            print(f"  - 現在: {current_location}")
            print(f"  - 前: {prev_location} (index={i-1 if i > 0 else 'なし'})")
            print(f"  - 後: {next_location} (index={i+1 if i < len(sorted_entries)-1 else 'なし'})")
            print(f"  - capture_time: {current_sp.capture_time if current_sp else 'なし'}")
            print(f"  - needs_location: {current_sp.needs('location') if current_sp else 'なし'}")
        
        # 近接画像からの補完
        supplemented_sp = current_sp.supplemented_by_closest(
            prev_sp, next_sp, TIME_WINDOW_SEC, keys=["location", "date_count"]
        )
        
        # 補完状況をデバッグ出力
        original_location = current_sp.get('location') if current_sp else None
        supplemented_location = supplemented_sp.get('location')
        if original_location != supplemented_location and entry.image_path:
            filename = os.path.basename(entry.image_path)
            print(f"DEBUG: 補完実行 {filename}: '{original_location}' -> '{supplemented_location}'")
        
        final_results.append(supplemented_sp.to_dict())
        # 後続エントリの補完に利用できるよう、エントリ自身を更新
        sorted_entries[i].survey_point = supplemented_sp
        entry.survey_point = supplemented_sp  # 元のリストにも反映
        
        print(f"DEBUG: {i+1:2d}. {os.path.basename(entry.image_path) if entry.image_path else 'None'}")
    
    # --- 後向きパスでもう一度補完（日付台数など前側から補完） ---
    for i in reversed(range(len(sorted_entries))):
        entry = sorted_entries[i]
        sp = entry.survey_point
        if sp is None or not sp.needs("date_count"):
            continue
        # 後ろ側 (次) を優先する
        next_sp = None
        for j in range(i+1, len(sorted_entries)):
            if sorted_entries[j].survey_point is not None:
                next_sp = sorted_entries[j].survey_point
                break
        if next_sp is None:
            continue
        supplemented = sp.supplement_from(next_sp, keys=["date_count"])
        if supplemented:
            entry.survey_point = sp
            final_results[i] = sp.to_dict()
    
    print(f"DEBUG: 最終結果数: {len(final_results)}")
    return final_results

def process_caption_board_ocr(args):
    """ImageEntry中心の新しいパイプライン処理"""
    # --verbose/-v が無ければ quiet モード（詳細ログ抑止）
    verbose = any(arg in ('-v', '--verbose') for arg in args[1:])

    # 最初の位置引数（ファイル名）を抽出
    non_option_args = [a for a in args[1:] if not a.startswith('-')]
    target_filename = non_option_args[0] if non_option_args else None

    # quiet モードなら stdout を一時的に抑止
    import sys as _sys, io as _io, contextlib as _ctx
    _original_stdout = _sys.stdout
    _suppress_ctx = _ctx.nullcontext()
    if not verbose:
        _suppress_ctx = _ctx.redirect_stdout(_io.StringIO())

    with _suppress_ctx:
        # 1. ImageEntryListを作成
        image_entries = _load_image_entries(target_filename)
        if not image_entries.entries:
            print("処理対象の画像が見つかりません")
            return

        # 2. OCRパイプラインを初期化
        pipeline = CaptionBoardOCRPipeline(project_root, src_dir)
        if not pipeline.initialize_engine():
            print("OCRエンジンの初期化に失敗しました")
            return

        # 3. 各ImageEntryに対してOCR処理を実行
        for entry in image_entries.entries:
            pipeline.process_image_entry(entry)

        # 4. SurveyPointの補完処理
        final_results = _supplement_survey_points(image_entries)

    # stdout 復帰後にサマリーのみ出力
    _sys.stdout = _original_stdout

    print_extracted_results_summary(final_results)
    save_success_results(final_results, project_root)

if __name__ == "__main__":
    process_caption_board_ocr(sys.argv)
