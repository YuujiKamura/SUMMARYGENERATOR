# --- Copied from src/thermometer_utils.py ---
import os
import collections
import re
from .records_loader import load_records_from_json

def thermometer_remarks_index(idx, group_size=3, num_candidates=4):
    return (idx // group_size) % num_candidates

def extract_number(filename):
    m = re.search(r'(\d+)', filename)
    return int(m.group(1)) if m else -1

THERMO_REMARKS = [
    "As混合物温度管理到着温度測定",
    "As混合物温度管理敷均し温度測定",
    "As混合物温度管理初期締固前温度",
    "As混合物温度管理開放温度測定"
]

def assign_thermometer_remarks(
    image_paths, remarks_list=None, image_roles=None, image_labels=None,
    group_size=3, records_path=None, debug_lines=None
):
    if remarks_list is None:
        if records_path is None:
            raise ValueError("remarks_listかrecords_pathのどちらかは必須です")
        records = load_records_from_json(records_path)
        remarks_list = [
            r['remarks'] for r in records
            if isinstance(r, dict) and r.get('remarks') in THERMO_REMARKS
        ]
        remarks_list = [r for r in THERMO_REMARKS if r in remarks_list]
        if len(remarks_list) != len(THERMO_REMARKS):
            raise ValueError(
                f"records_path={records_path} から温度管理用remarks({THERMO_REMARKS})が全て抽出できませんでした。"
                "辞書ファイルを確認してください。"
            )
    open_remarks = [
        r for r in remarks_list if ("開放温度" in r or "開放前温度" in r)
    ]
    normal_remarks = [r for r in remarks_list if r not in open_remarks]
    folder_to_images = collections.defaultdict(list)
    if debug_lines is not None:
        debug_lines.append(f"[DEBUG] assign_thermometer_remarks呼び出し: image_paths={image_paths}")
    for img_path in image_paths:
        parent = os.path.normcase(os.path.dirname(img_path))
        folder_to_images[parent].append(img_path)
    if debug_lines is not None:
        debug_lines.append(f"[DEBUG] folder_to_images keys: {list(folder_to_images.keys())}")
        for k, v in folder_to_images.items():
            debug_lines.append(f"[DEBUG] folder={k} → {[os.path.basename(p) for p in v]}")
    result = {}
    for folder, imgs in folder_to_images.items():
        all_targets = sorted(
            imgs, key=lambda x: extract_number(os.path.basename(x))
        )
        n = len(all_targets)
        if debug_lines is not None:
            debug_lines.append(
                f"[温度管理判定] フォルダ: {folder} 全{n}枚 (3枚ワンセットで区分、末尾3枚は開放温度)"
            )
            debug_lines.append(f"[DEBUG] 温度計画像群({n}枚): {[os.path.basename(p) for p in all_targets]}")
            debug_lines.append(f"[DEBUG] all_targets構築根拠: imgs={imgs} → all_targets={all_targets}")
        for i, img_path in enumerate(all_targets):
            if n - i <= 3 and open_remarks:
                rec = (
                    open_remarks[i - (n - 3)]
                    if (i - (n - 3)) < len(open_remarks)
                    else open_remarks[-1]
                )
                result[img_path] = rec
                if debug_lines is not None:
                    debug_lines.append(
                        f"  [開放温度] {os.path.basename(img_path)} "
                        f"({i+1}/{n}枚目)\n→ {rec}"
                    )
            else:
                if normal_remarks:
                    set_idx = (i // group_size) % len(normal_remarks)
                    rec = normal_remarks[set_idx]
                else:
                    rec = None
                result[img_path] = rec
                if debug_lines is not None:
                    debug_lines.append(
                        f"  [セット{set_idx+1}] {os.path.basename(img_path)} "
                        f"({i+1}/{n}枚目)\n→ {rec}"
                    )
    return result

def select_thermometer_remark(candidates_list):
    selected = []
    for idx, candidates in enumerate(candidates_list):
        sel_idx = thermometer_remarks_index(idx)
        if candidates and len(candidates) > sel_idx:
            selected.append(candidates[sel_idx])
        else:
            selected.append(None)
    return selected

def assign_thermometer_remarks_for_records(image_paths, records, image_roles=None, image_labels=None, group_size=3, debug_lines=None):
    remarks_list = [getattr(r, 'remarks', None) if hasattr(r, 'remarks') else r.get('remarks', None) for r in records]
    return assign_thermometer_remarks(image_paths, remarks_list, image_roles, image_labels, group_size, debug_lines)

def process_thermometer_records(candidates_list, debug_entries=None):
    final_selected = []
    total = len(candidates_list)
    if debug_entries:
        for i, entry in enumerate(debug_entries):
            entry.debug_log.append(f"[温度管理サイクルマッチング] 全体候補枚数: {total}枚 (この画像は{(i+1)}枚目, idx={i})")
    for idx, candidates in enumerate(candidates_list):
        filtered = [c for c in candidates if (getattr(c, 'remarks', None) and "温度測定" in getattr(c, 'remarks', '')) or (isinstance(c, dict) and "温度測定" in c.get('remarks', ''))]
        sel_idx = thermometer_remarks_index(idx)
        log_prefix = f"[温度管理サイクルマッチング] idx={idx}, sel_idx={sel_idx}, 候補数={len(filtered)}"
        if debug_entries and idx < len(debug_entries):
            entry = debug_entries[idx]
            entry.debug_log.append(f"{log_prefix} (全体{total}枚中{idx+1}枚目)")
        if filtered and len(filtered) > sel_idx:
            selected = filtered[sel_idx]
            assign_log = f"{log_prefix}, remarks={getattr(selected, 'remarks', None)} → アサイン"
            if debug_entries and idx < len(debug_entries):
                entry.debug_log.append(assign_log)
            final_selected.append(selected)
        else:
            if debug_entries and idx < len(debug_entries):
                entry.debug_log.append(f"{log_prefix} → アサインなし")
            final_selected.append(None)
    return final_selected

def process_thermometer_remarks(candidates_list):
    final_selected = []
    for idx, candidates in enumerate(candidates_list):
        filtered = [c for c in candidates if "温度測定" in c.get('remarks', '')]
        sel_idx = thermometer_remarks_index(idx)
        if filtered and len(filtered) > sel_idx:
            selected = filtered[sel_idx]
        else:
            selected = None
        final_selected.append(selected)
    return final_selected
