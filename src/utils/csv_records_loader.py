import csv
from pathlib import Path
from typing import List, Tuple, Dict
from .chain_record_utils import ChainRecord

def load_records_and_roles_csv(csv_path: Path) -> Tuple[List[ChainRecord], Dict[str, Dict]]:
    """CSV を読み込み ChainRecord リストと role_mapping 辞書を返す。
    CSV カラム:
    photo_category,work category,type,subtype,remarks,match,machine,driver/worker,board,mesurer,object,surface
    roles 列は複数行・カンマ区切り両方許容。
    """
    records: List[ChainRecord] = []
    mappings: Dict[str, Dict] = {}

    if not csv_path.exists():
        return records, mappings

    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            photo_category = row.get("photo_category", "").strip()
            work_category = row.get("work category", "").strip()
            type_ = row.get("type", "").strip()
            subtype = row.get("subtype", "").strip()
            remarks = row.get("remarks", "").strip()
            match_val = row.get("match", "any").strip().lower() or "any"

            rec = ChainRecord(
                photo_category=photo_category or None,
                work_category=work_category or None,
                type=type_ or None,
                subtype=subtype or None,
                remarks=remarks
            )

            role_cols = ["machine", "driver/worker", "board", "mesurer", "object", "surface"]
            roles: List[str] = []
            for col in role_cols:
                val = row.get(col, "")
                if val:
                    # セル内改行やカンマで分割
                    for part in val.replace("\n", ",").split(","):
                        p = part.strip()
                        if p:
                            roles.append(p)
            mappings[remarks] = {"roles": roles, "match": match_val}

            # 役割リストを保持
            if roles:
                rec.extra["roles"] = roles
                # 動的属性としても付与
                setattr(rec, "roles", roles)
            records.append(rec)

    return records, mappings 