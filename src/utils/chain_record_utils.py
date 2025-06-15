from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import json
import os

@dataclass
class ChainRecord:
    location: Optional[str] = None
    controls: List[str] = field(default_factory=list)
    photo_category: Optional[str] = None
    work_category: Optional[str] = None
    type: Optional[str] = None
    subtype: Optional[str] = None
    remarks: str = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_dict(d: dict) -> 'ChainRecord':
        # typo修正: photo_categgory→photo_category
        if 'photo_categgory' in d and 'photo_category' not in d:
            d['photo_category'] = d['photo_categgory']
        # category→work_categoryの自動補完
        if 'category' in d and not d.get('work_category'):
            d['work_category'] = d['category']
        # controls: control, controls, 管理値, などの多様なキーに対応
        controls = d.get('controls')
        if controls is None:
            # 旧データや単数形対応
            c = d.get('control') or d.get('管理値')
            if c is not None:
                if isinstance(c, list):
                    controls = c
                else:
                    controls = [c]
            else:
                controls = []
        # 主要フィールド以外はextraに格納
        known = {k: d.get(k) for k in ['location', 'photo_category', 'work_category', 'type', 'subtype', 'remarks']}
        known['controls'] = controls
        import json as _json
        extra = {k: v for k, v in d.items() if k not in known and k not in ['control', 'controls', '管理値']}
        # extra_json フィールドがあればマージ
        if 'extra_json' in d and d['extra_json']:
            try:
                decoded = _json.loads(d['extra_json']) if isinstance(d['extra_json'], str) else d['extra_json']
                if isinstance(decoded, dict):
                    extra.update(decoded)
            except Exception:
                pass
        # extra_jsonキー自体は不要
        extra.pop('extra_json', None)

        rec = ChainRecord(**known, extra=extra)
        if isinstance(extra, dict) and 'roles' in extra and extra['roles']:
            setattr(rec, 'roles', extra['roles'])
        return rec

    def to_dict(self) -> dict:
        d = {
            'location': self.location,
            'controls': self.controls,
            'photo_category': self.photo_category,
            'work_category': self.work_category,
            'type': self.type,
            'subtype': self.subtype,
            'remarks': self.remarks,
        }
        # extraの内容も展開
        if self.extra:
            d.update(self.extra)
        # None値は除外
        return {k: v for k, v in d.items() if v is not None}

    def __hash__(self):
        # remarksは必須、それ以外はNone許容
        return hash((
            self.remarks,
            self.photo_category,
            self.work_category,
            self.type,
            self.subtype,
            self.location,
            self.controls
        ))

def load_chain_records(json_path: str) -> List[ChainRecord]:
    """
    default_records.json（参照型・従来型両対応）からChainRecordのリストを返す
    """
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    records = data.get("records", [])
    # 参照型（パスリスト）なら各ファイルを読み込む
    if records and isinstance(records[0], str):
        base_dir = os.path.dirname(json_path)
        loaded = []
        for rec_path in records:
            if os.path.isabs(rec_path):
                rec_abspath = rec_path
            else:
                rec_abspath = os.path.normpath(os.path.join(base_dir, rec_path.lstrip('./\\')))
            with open(rec_abspath, encoding="utf-8") as rf:
                rec_data = json.load(rf)
                if not isinstance(rec_data, dict):
                    print(f"[WARN] {rec_abspath} の内容がdictではありません: {type(rec_data)}")
                    continue
                loaded.append(ChainRecord.from_dict(rec_data))
        return loaded
    # 従来型（リスト of dict）
    else:
        return [ChainRecord.from_dict(r) for r in records if isinstance(r, dict)]

def find_chain_records_by_roles(roles: List[str], records: List[ChainRecord]) -> List[ChainRecord]:
    """
    rolesリストのいずれかがChainRecordの属性（work_category/type/subtype/extra等）に含まれていればマッチとみなす。
    """
    matched = []
    for rec in records:
        rec_roles = set()
        # work_category/type/subtype/extraの値をroles候補とみなす
        for attr in [rec.work_category, rec.type, rec.subtype]:
            if attr:
                rec_roles.add(attr)
        # extra(dict)の値もroles候補に加える
        if rec.extra:
            for v in rec.extra.values():
                if isinstance(v, str):
                    rec_roles.add(v)
                elif isinstance(v, list):
                    rec_roles.update([str(x) for x in v])
        # rolesのいずれかがrec_rolesに含まれていればマッチ
        if any(r in rec_roles for r in roles):
            matched.append(rec)
    return matched

def dictrecord_to_chainrecord(drec) -> ChainRecord:
    """
    DictRecordインスタンスまたはdictをChainRecordに変換（フィールド名が一致していればOK）
    """
    if hasattr(drec, 'to_dict'):
        d = drec.to_dict()
    else:
        d = dict(drec)
    return ChainRecord.from_dict(d)

# save_chain_records: DictRecord/ChainRecord両対応
def save_chain_records(json_path: str, records: list) -> None:
    """
    ChainRecordまたはDictRecordのリストを default_records.json 互換形式で保存する。
    辞書管理ウィジェットのDictRecordリストもそのまま保存可能。
    """
    def record_to_dict(rec) -> dict:
        if hasattr(rec, 'to_dict'):
            d = rec.to_dict()
        elif hasattr(rec, '__dict__'):
            d = dict(rec.__dict__)
        else:
            d = dict(rec)
        # extraの内容も展開（ChainRecordの場合）
        if 'extra' in d and isinstance(d['extra'], dict):
            d.update(d['extra'])
            del d['extra']
        # None値は除外
        return {k: v for k, v in d.items() if v is not None}
    data = {"records": [record_to_dict(r) for r in records]}
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)