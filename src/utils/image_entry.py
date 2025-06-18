from typing import List, Optional, TYPE_CHECKING
import os

if TYPE_CHECKING:
    from ocr_tools.survey_point import SurveyPoint

class ImageEntry:
    def __init__(self, image_path: Optional[str] = None, json_path: Optional[str] = None, chain_records: Optional[list] = None, location: Optional[str] = None, debug_text: Optional[str] = None, cache_json: Optional[dict] = None, roles: Optional[list] = None, survey_point: Optional['SurveyPoint'] = None, filename: Optional[str] = None):
        self.image_path = image_path
        self.json_path = json_path
        self.chain_records = chain_records or []
        self.location = location
        self.debug_text = debug_text
        self.cache_json = cache_json
        self.roles = roles or []
        self.survey_point: Optional['SurveyPoint'] = survey_point  # SurveyPointオブジェクト
        self.debug_log: list[str] = []
        
        # filenameプロパティを追加（image_pathから自動推論も可能）
        if filename:
            self.filename = filename
        elif image_path:
            self.filename = os.path.basename(image_path)
        else:
            self.filename = None
        # print(f"[DEBUG][ImageEntry.__init__] image_path={self.image_path}, roles={self.roles}, chain_records={[getattr(r, 'remarks', None) for r in self.chain_records]}, id={id(self)}, cache_json_keys={list(self.cache_json.keys()) if self.cache_json else None}")

    def get_cache_json_path(self, cache_dir: Optional[str] = None) -> Optional[str]:
        """画像パスからSHAハッシュベースのキャッシュJSONパスを取得"""
        if not self.image_path:
            return None
        
        from .image_cache_utils import get_image_cache_path
        return get_image_cache_path(self.image_path, cache_dir)
    
    def load_cache_json(self, cache_dir: Optional[str] = None) -> Optional[dict]:
        """キャッシュJSONを読み込み、cache_jsonプロパティに設定"""
        if not self.image_path:
            return None
            
        from .image_cache_utils import load_image_cache
        data = load_image_cache(self.image_path, cache_dir, return_full=True)
        if data and isinstance(data, dict):
            # そのまま保持（image_path, bboxes, survey_point など全て含む）
            self.cache_json = data
            return self.cache_json
        return None
    
    def has_caption_board_bbox(self) -> bool:
        """キャッシュJSONにキャプションボードのbboxが含まれているかチェック。
        master JSON (image_preview_cache_master) には古いbboxしか載っておらず、
        caption_board が欠落している場合がある。その場合は SHA ハッシュ JSON を
        自動的に再読み込みして再判定する。"""
        # 1st: 現在保持している cache_json で判定
        if self._check_caption_board_in_bboxes(self.cache_json):
            return True

        # 2nd: SHAハッシュベースのキャッシュをロードして再判定
        loaded = self.load_cache_json()
        if loaded and self._check_caption_board_in_bboxes(loaded):
            return True

        return False

    @staticmethod
    def _check_caption_board_in_bboxes(cache_json: Optional[dict]) -> bool:
        if not cache_json:
            return False
        bboxes = cache_json.get('bboxes', [])
        for bbox in bboxes:
            cname = (bbox.get('cname') or '').lower()
            role = (bbox.get('role') or '').lower()
            if 'caption_board' in cname or 'caption_board' in role:
                return True
        return False
    
    def get_caption_board_bbox(self) -> Optional[dict]:
        """キャプションボードのbboxを取得"""
        if not self.cache_json:
            return None
        
        bboxes = self.cache_json.get('bboxes', [])
        for bbox in bboxes:
            cname = bbox.get('cname', '') or ''
            role = bbox.get('role', '') or ''
            if 'caption_board' in cname or 'caption_board' in role:
                return bbox
        return None

    @classmethod
    def from_cache_json(cls, image_path, cache_json, role_mapping, records):
        # roles抽出
        print(f"[DEBUG][from_cache_json] image_path={image_path}")
        print(f"[DEBUG][from_cache_json] cache_json keys={list(cache_json.keys()) if cache_json else None}")
        roles = []
        if cache_json:
            if "roles" in cache_json and isinstance(cache_json["roles"], list):
                roles = cache_json["roles"]
                print(f"[DEBUG][from_cache_json] roles from cache_json['roles']: {roles}")
            elif "bboxes" in cache_json:
                print(f"[DEBUG][from_cache_json] bboxes: {cache_json['bboxes']}")
                for b in cache_json["bboxes"]:
                    if "role" in b and b["role"]:
                        roles.append(b["role"])
                print(f"[DEBUG][from_cache_json] roles from bboxes: {roles}")
            else:
                print("[DEBUG][from_cache_json] roles not found in cache_json")
        else:
            print("[DEBUG][from_cache_json] cache_json is None")
        img_json = {"roles": roles}
        if cache_json:
            img_json.update(cache_json)
        # chain_recordsをマッチング
        from .record_matching_utils import match_roles_records_one_stop
        matched_entry = match_roles_records_one_stop(img_json, role_mapping, records, image_path=image_path, json_path=cache_json)
        # location, debug_textもセット
        result = cls(
            image_path=image_path,
            json_path=cache_json,
            chain_records=matched_entry.chain_records,
            location=img_json.get('location', None),
            debug_text=img_json.get('debug_text', None)        )
        # debug_logを引き継ぐ
        result.debug_log = getattr(matched_entry, 'debug_log', []).copy()
        return result
    
    def __repr__(self):
        return f"ImageEntry(image_path={self.image_path}, chain_records={self.chain_records})"

    # --- compatibility aliases ---
    @property
    def path(self):
        """Alias for image_path to maintain backward compatibility with legacy code."""
        return self.image_path

    @path.setter
    def path(self, value: str):
        self.image_path = value
    
    def get_capture_time(self) -> Optional[float]:
        """画像の撮影時刻を取得（EXIFから）"""
        if not self.image_path:
            return None
        try:
            # 上位ディレクトリのocr_toolsへのパス解決
            import sys
            import os
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            ocr_tools_dir = os.path.join(project_root, 'ocr_tools')
            if ocr_tools_dir not in sys.path:
                sys.path.insert(0, ocr_tools_dir)
            
            from exif_utils import get_capture_time_with_fallback
            return get_capture_time_with_fallback(self.image_path)
        except ImportError:
            # exif_utilsが見つからない場合はNoneを返す
            return None
        except Exception:
            return None

    def initialize_capture_time(self):
        """撮影時刻を取得してSurveyPointに設定"""
        if not self.survey_point:
            return
        
        if self.survey_point.capture_time is None:
            capture_time = self.get_capture_time()
            if capture_time:
                self.survey_point.capture_time = capture_time

    def supplement_missing_fields(self, other_entries: List['ImageEntry'], time_window_sec: int = 300) -> bool:
        """不足している情報を他のエントリから補完"""
        if not self.survey_point:
            return False
        
        # 撮影時刻を初期化
        self.initialize_capture_time()
        
        if self.survey_point.capture_time is None:
            return False
        
        # 時系列で前後のエントリを探す
        prev_entry, next_entry = self._find_adjacent_entries(other_entries)
        
        # 補完を実行
        return self._apply_supplement(prev_entry, next_entry, time_window_sec)
    
    def _find_adjacent_entries(self, other_entries: List['ImageEntry']) -> tuple[Optional['ImageEntry'], Optional['ImageEntry']]:
        """時系列で前後のエントリを見つける"""
        if not self.survey_point or self.survey_point.capture_time is None:
            return None, None
        
        my_time = self.survey_point.capture_time
        prev_entry = None
        next_entry = None
        
        for entry in other_entries:
            if entry == self or not entry.survey_point:
                continue
            
            # 他のエントリも撮影時刻を初期化
            entry.initialize_capture_time()
            other_time = entry.survey_point.capture_time
            if other_time is None:
                continue
                
            if other_time < my_time:
                if prev_entry is None or (prev_entry.survey_point and prev_entry.survey_point.capture_time is not None and other_time > prev_entry.survey_point.capture_time):
                    prev_entry = entry
            elif other_time > my_time:
                if next_entry is None or (next_entry.survey_point and next_entry.survey_point.capture_time is not None and other_time < next_entry.survey_point.capture_time):
                    next_entry = entry
        
        return prev_entry, next_entry

    def _apply_supplement(self, prev_entry: Optional['ImageEntry'], next_entry: Optional['ImageEntry'], time_window_sec: int) -> bool:
        """実際の補完処理を実行"""
        if not self.survey_point:
            return False
        
        my_time = self.survey_point.capture_time
        if my_time is None:
            return False
        
        # 補完候補を距離とともに収集
        candidates = []
        for entry in [prev_entry, next_entry]:
            if entry and entry.survey_point and entry.survey_point.capture_time is not None:
                time_diff = abs(entry.survey_point.capture_time - my_time)
                candidates.append((time_diff, entry.survey_point))
        
        if not candidates:
            return False
        
        # 最も近い候補を選択
        time_diff, closest_survey_point = min(candidates, key=lambda x: x[0])
        
        # 時間窓を超える場合は補完しない
        if time_diff > time_window_sec:
            return False
        
        # 補完を実行
        return self.survey_point.supplement_from(closest_survey_point)

class ImageEntryList:
    """
    画像エントリー群（温度管理写真群・品質管理写真群など）を表現するデータクラス。
    entries: List[ImageEntry]
    group_type: str  # 例: '品質管理写真群', '温度管理写真群' など    その他、群単位の属性やメソッドを拡張可能
    """
    
    def __init__(self, entries: Optional[List[ImageEntry]] = None, group_type: Optional[str] = None):
        self.entries = entries if entries is not None else []
        self.group_type = group_type
        self.debug_log: list[str] = []  # 群単位のデバッグ用ログ

    def __len__(self):
        return len(self.entries)

    def __getitem__(self, idx):
        return self.entries[idx]

    def append(self, entry: ImageEntry):
        self.entries.append(entry)
    
    def add_entry(self, entry: ImageEntry):
        """entryを追加（appendのエイリアス）"""
        self.entries.append(entry)

    def __repr__(self):
        return f"ImageEntryList(group_type={self.group_type}, entries={self.entries})"