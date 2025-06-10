import os
from src.utils.path_manager import path_manager
# 画像選択時のデバッグログ生成ユーティリティ

def generate_image_selection_debug(entry, data_service, matched_remarks, debug_lines, role_mapping=None):
    """
    画像選択時のデバッグログ生成（remarks, records, entry, debug_linesをまとめてテキスト化）
    出来形判定の場合は、管理図ボードの割合・判定・最終選択remarksを明示的に表示。
    温度管理マッチングの場合は、サイクル割り当て根拠・末尾3枚の開放温度割当も明示的に表示。
    """
    print(f"[DEBUG] generate_image_selection_debug: debug_lines = {debug_lines}")
    from src.utils.records_loader import load_records_from_json
    records = data_service.dictionary_manager.records
    # ChainRecord対応: remarks_to_recordの生成
    remarks_to_record = {getattr(r, 'remarks', None): r for r in records if getattr(r, 'remarks', None)}
    try:
        # 1. ロールマッピング
        mapping_path = path_manager.role_mapping
        mapping_count = 0
        if role_mapping:
            mapping_count = len(role_mapping)
            debug_lines.append(f"[ロールマッピング] path={mapping_path}, {mapping_count}件")
        else:
            debug_lines.append(f"[ロールマッピング] ロード失敗 or 空 (path={mapping_path})")
        # 2. 画像ロール
        roles = None
        if hasattr(entry, 'cache_json') and entry.cache_json:
            bboxes = entry.cache_json.get('bboxes', [])
            roles = [b.get('role') for b in bboxes if b.get('role')]
        elif hasattr(entry, 'roles'):
            roles = getattr(entry, 'roles')
        debug_lines.append(f"[画像ロール] {roles if roles is not None else 'None'}")
        # 3. 判定基準
        debug_lines.append(f"[判定基準] {mapping_count}件のremarksにroles割当")
        # --- 温度管理マッチングの判定過程を明示的に表示 ---
        from src.thermometer_utils import THERMO_REMARKS
        is_thermo = False
        if matched_remarks and any(r for r in matched_remarks if hasattr(r, 'remarks') and r.remarks in THERMO_REMARKS):
            is_thermo = True
        if is_thermo:
            debug_lines.append("[温度管理マッチング] サイクル割り当て根拠:")
            # 画像リスト内でのインデックス・remarks割当を明示
            # entry.pathが属するフォルダ内の温度計画像リストを取得
            folder = os.path.dirname(entry.path)
            # recordsから温度管理remarksのみ抽出
            thermo_remarks = [r for r in records if getattr(r, 'remarks', None) in THERMO_REMARKS]
            debug_lines.append(f"  温度管理remarks候補: {[r.remarks for r in thermo_remarks]}")
            # フォルダ内の画像リストを取得
            import glob
            img_list = sorted(glob.glob(os.path.join(folder, '*.JPG')) + glob.glob(os.path.join(folder, '*.jpg')))
            # ファイル名昇順でインデックスを決定
            if entry.path in img_list:
                idx = img_list.index(entry.path)
                n = len(img_list)
                debug_lines.append(f"  フォルダ内画像枚数: {n} / この画像のインデックス: {idx+1}")
                if n - idx <= 3:
                    debug_lines.append(f"  → 末尾3枚なので '開放温度' 割当")
                else:
                    set_idx = (idx // 3) % (len(THERMO_REMARKS)-1)
                    debug_lines.append(f"  → サイクル順序: {set_idx+1}番目 ({THERMO_REMARKS[set_idx]})")
            else:
                debug_lines.append(f"  [WARN] entry.pathがフォルダ内画像リストに見つかりません: {entry.path}")
        # 4. 判定結果
        if matched_remarks:
            if hasattr(matched_remarks[0], 'remarks'):
                result_list = [r.remarks for r in matched_remarks]
            else:
                result_list = matched_remarks
            debug_lines.append(f"[判定結果] {result_list}")
        else:
            debug_lines.append("[判定結果] なし")
        # 出来形判定のログ・判定値をdebug_linesから抽出
        ratio = None
        is_closeup = None
        for line in debug_lines:
            if 'caption_board_dekigata判定' in line:
                # 例: ...caption_board_dekigata判定: is_closeup=False, ratio=0.0102...
                import re
                m = re.search(r'is_closeup=([A-Za-z]+), ratio=([0-9.]+)', line)
                if m:
                    is_closeup = m.group(1)
                    ratio = m.group(2)
        # 出来形remarksのみ抽出（ChainRecord対応）
        dekigata_remarks = [r for r in matched_remarks if hasattr(r, 'remarks') and '出来形' in r.remarks]
        # 最終的な選択肢（全景/接写どちらか一方のみ）
        final_remark = None
        for r in dekigata_remarks:
            if '全景' in r.remarks or '接写' in r.remarks:
                final_remark = r.remarks
                break
        # 管理値特例（管理値のみの場合）
        if not final_remark and dekigata_remarks:
            for r in dekigata_remarks:
                if '管理値' in r.remarks:
                    final_remark = r.remarks
                    break
        # 出力
        if dekigata_remarks:
            lines = ["[出来形判定結果]"]
            if ratio is not None and is_closeup is not None:
                # is_closeup の値に基づいて判定文字列を決定
                hantei_str = "管理値" if is_closeup == 'None' else ('接写' if is_closeup == 'True' else '全景')
                lines.append(f"  管理図ボード割合: {ratio} / 判定: {hantei_str}")
            elif ratio is not None:
                lines.append(f"  管理図ボード割合: {ratio}")
            if final_remark:
                lines.append(f"  最終選択 remarks: {final_remark}")
            else:
                lines.append(f"  最終選択 remarks: なし（判定失敗）")
            # 追加: remarksパネルへのエントリー通知内容を明示
            lines.append("")
            lines.append("[remarksパネルへのエントリー通知]")
            for r in matched_remarks:
                if hasattr(r, 'remarks'):
                    lines.append(f"  → {r.remarks}")
                else:
                    lines.append(f"  → {r}")
            return '\n'.join(lines)
        # 通常の温度管理や他のマッチングは従来通り
        from src.utils.debug_utils import generate_matching_debug_log
        debug_lines2 = generate_matching_debug_log(matched_remarks, entry, indent_level=1)
        debug_text = '\n'.join(debug_lines2)
        return debug_text
    except Exception as e:
        return f"[デバッグログ生成エラー] {e}"
