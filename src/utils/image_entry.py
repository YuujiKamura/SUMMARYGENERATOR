from typing import List, Optional

class ImageEntry:
    def __init__(self, image_path: str = None, json_path: str = None, chain_records: list = None, location: str = None, debug_text: str = None, cache_json: dict = None, roles: list = None):
        self.image_path = image_path
        self.json_path = json_path
        self.chain_records = chain_records or []
        self.location = location
        self.debug_text = debug_text
        self.cache_json = cache_json
        self.roles = roles or []
        self.debug_log: list[str] = []
        print(f"[DEBUG][ImageEntry.__init__] image_path={self.image_path}, roles={self.roles}, chain_records={[getattr(r, 'remarks', None) for r in self.chain_records]}, id={id(self)}, cache_json_keys={list(self.cache_json.keys()) if self.cache_json else None}")

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
                print(f"[DEBUG][from_cache_json] roles not found in cache_json")
        else:
            print(f"[DEBUG][from_cache_json] cache_json is None")
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
            debug_text=img_json.get('debug_text', None)
        )
        # debug_logを引き継ぐ
        result.debug_log = getattr(matched_entry, 'debug_log', []).copy()
        return result

    def __repr__(self):
        return f"ImageEntry(image_path={self.image_path}, chain_records={self.chain_records})"

class ImageEntryList:
    """
    画像エントリー群（温度管理写真群・品質管理写真群など）を表現するデータクラス。
    entries: List[ImageEntry]
    group_type: str  # 例: '品質管理写真群', '温度管理写真群' など
    その他、群単位の属性やメソッドを拡張可能
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

    def __repr__(self):
        return f"ImageEntryList(group_type={self.group_type}, entries={self.entries})"