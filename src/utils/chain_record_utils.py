# --- Copied from src/utils/chain_record_utils.py ---
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import json
import os

@dataclass
class ChainRecord:
    remarks: str
    photo_category: Optional[str] = None
    work_category: Optional[str] = None
    type: Optional[str] = None
    subtype: Optional[str] = None
    control: Optional[str] = None
    station: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    @staticmethod
    def from_dict(d: dict) -> 'ChainRecord':
        if 'photo_categgory' in d and 'photo_category' not in d:
            d['photo_category'] = d['photo_categgory']
        if 'category' in d and not d.get('work_category'):
            d['work_category'] = d['category']
        known = {k: d.get(k) for k in ['remarks', 'photo_category', 'work_category', 'type', 'subtype', 'control', 'station']}
        extra = {k: v for k, v in d.items() if k not in known}
        return ChainRecord(**known, extra=extra)
    def to_dict(self) -> dict:
        d = {
            'remarks': self.remarks,
            'photo_category': self.photo_category,
            'work_category': self.work_category,
            'type': self.type,
            'subtype': self.subtype,
            'control': self.control,
            'station': self.station,
        }
        if self.extra:
            d.update(self.extra)
        return {k: v for k, v in d.items() if v is not None}
    def __hash__(self):
        return hash((
            self.remarks,
            self.photo_category,
            self.work_category,
            self.type,
            self.subtype,
            self.control,
            self.station
        ))
def load_chain_records(json_path: str) -> List[ChainRecord]:
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    records = data.get("records", [])
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
    else:
        return [ChainRecord.from_dict(r) for r in records if isinstance(r, dict)]
def find_chain_records_by_roles(roles: List[str], records: List[ChainRecord]) -> List[ChainRecord]:
    matched = []
    for rec in records:
        rec_roles = set()
        for attr in [rec.work_category, rec.type, rec.subtype]:
            if attr:
                rec_roles.add(attr)
        if rec.extra:
            for v in rec.extra.values():
                if isinstance(v, str):
                    rec_roles.add(v)
                elif isinstance(v, list):
                    rec_roles.update([str(x) for x in v])
        if any(r in rec_roles for r in roles):
            matched.append(rec)
    return matched
def dictrecord_to_chainrecord(drec) -> ChainRecord:
    if hasattr(drec, 'to_dict'):
        d = drec.to_dict()
    else:
        d = dict(drec)
    return ChainRecord.from_dict(d)
def save_chain_records(json_path: str, records: list) -> None:
    def record_to_dict(rec) -> dict:
        if hasattr(rec, 'to_dict'):
            d = rec.to_dict()
        elif hasattr(rec, '__dict__'):
            d = dict(rec.__dict__)
        else:
            d = dict(rec)
        if 'extra' in d and isinstance(d['extra'], dict):
            d.update(d['extra'])
            del d['extra']
        return {k: v for k, v in d.items() if v is not None}
    data = {"records": [record_to_dict(r) for r in records]}
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
