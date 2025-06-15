"""
SummaryDataService: サマリー生成用のデータサービス
"""
import sys
import os
from pathlib import Path

# パスマネージャーを使用してプロジェクトルートを設定
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.utils.chain_record_utils import ChainRecord, find_chain_records_by_roles
from src.utils.image_entry import ImageEntry
from typing import Optional, Callable, List, Dict, Any
import logging
from src.db_manager import (
    ChainRecordManager, RoleMappingManager, ImageManager, BBoxManager
)
import json
from src.services.db_resource_service import DBResourceService
from src.services.image_matching_service import ImageMatchingService
from src.services.category_role_service import CategoryRoleService
from src.dictionary_manager import DictionaryManager

def is_thermometer_entry(entry):
    roles = getattr(entry, 'roles', []) if hasattr(entry, 'roles') else []
    if not roles and hasattr(entry, 'cache_json') and entry.cache_json:
        if 'roles' in entry.cache_json:
            roles = entry.cache_json['roles']
        elif 'bboxes' in entry.cache_json:
            roles = [b.get('role') for b in entry.cache_json['bboxes'] if b.get('role')]
    return any(r and ("温度計" in r or "thermometer" in r) for r in roles)

class SummaryDataService:
    """
    サマリー生成用のデータサービス。画像リスト・マッチング・カテゴリ抽出等を担当。
    ファサードとして各専用サービスに処理を委譲する。
    """
    def __init__(self, db_path=None, dictionary_manager: Optional[Any] = None, cache_dir: Optional[str] = None, records_path: Optional[str] = None, settings_manager: Optional[Any] = None, role_mapping: Optional[dict] = None):
        self.db_path = db_path
        self.db_resource_service = DBResourceService()
        # DBアクセサをDIして ImageMatchingService を生成
        self.image_matching_service = ImageMatchingService(
            get_images_func=ImageManager.get_all_images,
            get_bboxes_func=BBoxManager.get_bboxes_for_image
        )
        self.category_role_service = CategoryRoleService()
        self.dictionary_manager = dictionary_manager or DictionaryManager(db_path)
        self.settings_manager = settings_manager
        self.cache_dir = cache_dir
        self.records_path = records_path
        self.role_mapping = role_mapping
        self.all_entries: List[ImageEntry] = []
        self.remarks_to_chain_record: Dict[str, ChainRecord] = {}
        self.image_roles: Dict[str, Dict[str, str]] = {}
        self.load_initial_data()
        self.full_initialize()

    def load_initial_data(self):
        raw_records = [
            ChainRecord.from_dict(r)
            for r in ChainRecordManager.get_all_chain_records()
        ]
        # 同一remarksはrolesを含む方を優先
        tmp = {}
        for rec in raw_records:
            key = rec.remarks
            has_roles = bool(rec.extra.get('roles')) if isinstance(rec.extra, dict) else False
            if key not in tmp:
                tmp[key] = rec
            else:
                prev = tmp[key]
                prev_has_roles = bool(prev.extra.get('roles')) if isinstance(prev.extra, dict) else False
                if has_roles and not prev_has_roles:
                    tmp[key] = rec
        self.all_records = list(tmp.values())
        
        # ロールマッピング読み込みを改善（エラーハンドリング強化）
        self.role_mappings = {}
        for row in RoleMappingManager.get_all_role_mappings():
            try:
                if row['mapping_json'] and row['mapping_json'].strip():
                    self.role_mappings[row['role_name']] = json.loads(row['mapping_json'])
                else:
                    self.role_mappings[row['role_name']] = {}
                    logging.debug(f"[ROLE_MAPPING] 空のマッピング: {row['role_name']}")
            except json.JSONDecodeError as e:
                logging.warning(f"[ROLE_MAPPING_ERROR] {row['role_name']}: {e} - データ: {row['mapping_json']}")
                self.role_mappings[row['role_name']] = {}
        
        logging.info(f"[ROLE_MAPPING_LOADED] 読み込み完了: {len(self.role_mappings)}件")
        
        if self.all_records:
            self.remarks_to_chain_record = {
                record.remarks: record
                for record in self.all_records
                if hasattr(record, 'remarks') and record.remarks
            }
            logging.info(f"[CHAIN_RECORDS_LOADED] レコード数: {len(self.remarks_to_chain_record)}")
        else:
            logging.warning("[CHAIN_RECORDS_EMPTY] ChainRecordが見つかりません")

    def set_all_entries(self, entries: List[ImageEntry]):
        logging.info(
            "[DEBUG][set_all_entries] 呼び出し: entriesの長さ=%d id_list=%s",
            len(entries), [id(e) for e in entries]
        )
        self.all_entries = entries
        for entry in entries:
            # logging.info(
            #     "[DEBUG][set_all_entries] entry: image_path=%s, id=%d, debug_log=%s",
            #     getattr(entry, 'image_path', None), id(entry), entry.debug_log
            # )
            # logging.info(
            #     "[DEBUG][SummaryDataService] image_path=%s, id=%d, chain_records=%s",
            #     getattr(entry, 'image_path', None), id(entry),
            #     [
            #         {'remarks': getattr(r, 'remarks', None),
            #          'photo_category': getattr(r, 'photo_category', None)}
            #         for r in getattr(entry, 'chain_records', [])
            #     ]
            # )
            pass
        # 旧サイクルマッチング（温度計ロール専用処理）は廃止。
        # ここでは何も追加マッチングを行わず、ImageMatchingService に一任する。
        logging.info("[DEBUG][set_all_entries] return直前: entriesのdebug_log一覧")
        for entry in entries:
            # logging.info(
            #     "  image_path=%s, id=%d, debug_log=%s",
            #     getattr(entry, 'image_path', None), id(entry), getattr(entry, 'debug_log', None)
            # )
            pass
        return

    def update_image_roles(self, image_path: str, roles: Dict[str, str]):
        self.image_roles[image_path] = roles

    def get_roles_for_image(self, image_path: str) -> Dict[str, str]:
        return self.image_roles.get(image_path, {})

    def get_categories(self, entries, match_results):
        return self.category_role_service.get_categories(self.all_records)

    def get_sorted_entries(self, entries, match_results, selected_cat, ascending):
        return self.category_role_service.get_sorted_entries(
            entries, match_results, selected_cat, ascending, self.all_records)

    def get_remarks_for_entry(self, entry: 'ImageEntry',
                              debug_callback: Optional[Callable[[str, str], None]] = None) -> List[ChainRecord]:
        return self.category_role_service.get_remarks_for_entry(
            entry, self.all_records, debug_callback)

    def get_photo_category_from_remarks(self, remarks: str) -> str:
        rec = self.remarks_to_chain_record.get(remarks)
        return rec.photo_category if rec and rec.photo_category is not None else ''

    def get_chain_records_for_image(self, img_path: str) -> list:
        roles = []
        if hasattr(self, 'image_roles') and img_path in self.image_roles:
            r = self.image_roles[img_path]
            if isinstance(r, dict):
                roles = list(r.values())
            else:
                roles = r
        records = getattr(self.dictionary_manager, 'records', [])
        return find_chain_records_by_roles(roles, records)

    def get_image_entry_for_image(self, img_path: str) -> Optional[ImageEntry]:
        for entry in self.all_entries:
            if hasattr(entry, 'image_path') and entry.image_path == img_path:
                return entry
        return None

    def import_chain_records_from_json(self, json_path=None):
        return self.db_resource_service.import_chain_records_from_json(json_path)

    def import_role_mappings_from_json(self, json_path=None):
        return self.db_resource_service.import_role_mappings_from_json(json_path)

    def import_image_entries_from_json(self, json_path=None):
        return self.db_resource_service.import_image_entries_from_json(json_path)

    def reset_all_resources(self):
        return self.db_resource_service.reset_all_resources()

    def get_match_results(self, entries, role_mapping, remarks_to_chain_record, debug_callback=None):
        import logging
        
        # ===== マッチング前データダンプ =====
        logging.info(f"[DATA_DUMP_START] エントリー数: {len(entries)}, ロールマッピング数: {len(role_mapping)}")
        
        # JSONファイルからロール情報を読み込み（テストスクリプトと同じソース）
        json_path = project_root / 'data' / 'image_preview_cache_master.json'
        try:
            sys.path.insert(0, str(project_root / 'data'))
            from data_loader import load_image_roles
            image_roles = load_image_roles(str(json_path))
            logging.info(f"[JSON_LOAD_SUCCESS] {len(image_roles)}枚の画像データを読み込み")
        except Exception as e:
            logging.error(f"[JSON_LOAD_ERROR] {e}")
            return {}
        
        # データ配置状況をダンプ
        logging.info(f"[DATA_DUMP] === マッチング前データ状況 ===")
        logging.info(f"[DATA_DUMP] entries数: {len(entries)}")
        logging.info(f"[DATA_DUMP] image_roles数: {len(image_roles)}")
        logging.info(f"[DATA_DUMP] remarks_to_chain_record数: {len(remarks_to_chain_record)}")
        
        # 全entriesのパスをダンプ
        logging.info(f"[DATA_DUMP_ALL_ENTRIES] 全画像パス:")
        for i, entry in enumerate(entries):
            img_path = getattr(entry, 'image_path', '')
            filename = img_path.split('\\')[-1] if img_path else 'N/A'
            logging.info(f"[DATA_DUMP_ENTRY_{i}] {filename}")
        
        # 全image_rolesのキーをダンプ
        logging.info(f"[DATA_DUMP_ALL_JSON] JSONの全画像パス:")
        for i, img_path in enumerate(list(image_roles.keys())[:10]):  # 最初の10件
            filename = img_path.split('\\')[-1] if img_path else 'N/A'
            logging.info(f"[DATA_DUMP_JSON_{i}] {filename}")
        
        # サンプル画像のロール情報をダンプ
        rimg8567_path = None
        for entry in entries[:5]:  # 最初の5枚をサンプル
            img_path = getattr(entry, 'image_path', '')
            if 'RIMG8567' in img_path:
                rimg8567_path = img_path
            json_roles = image_roles.get(img_path, [])
            logging.info(f"[DATA_DUMP_SAMPLE] {img_path.split('\\')[-1] if img_path else 'N/A'}: roles={json_roles}")
        
        # RIMG8567を明示的に検索
        for img_path in image_roles.keys():
            if 'RIMG8567' in img_path:
                logging.info(f"[DATA_DUMP_8567_FOUND_JSON] JSONに存在: {img_path}")
                break
        
        for entry in entries:
            img_path = getattr(entry, 'image_path', '')
            if 'RIMG8567' in img_path:
                logging.info(f"[DATA_DUMP_8567_FOUND_ENTRY] entriesに存在: {img_path}")
                rimg8567_path = img_path
                break
        
        if rimg8567_path:
            logging.info(f"[DATA_DUMP_8567] RIMG8567見つかった: {rimg8567_path}")
            logging.info(f"[DATA_DUMP_8567] ロール情報: {image_roles.get(rimg8567_path, [])}")
        else:
            logging.warning(f"[DATA_DUMP_8567] RIMG8567がentriesに見つからない")
        
        # ChainRecordサンプルをダンプ
        for i, (remarks, chain_record) in enumerate(list(remarks_to_chain_record.items())[:3]):
            logging.info(f"[DATA_DUMP_RECORD_{i}] {remarks}: category={getattr(chain_record, 'photo_category', 'N/A')}")
        
        logging.info(f"[DATA_DUMP] === マッチング実行開始 ===")
        
        # ===== CSV から matcher 用レコードをロード =====
        csv_path = project_root / 'data' / 'records_and_roles.csv'
        try:
            import importlib.machinery, importlib.util
            loader = importlib.machinery.SourceFileLoader('csv_loader', str(project_root / 'data' / 'data_loader.py'))
            spec = importlib.util.spec_from_loader(loader.name, loader)
            csv_loader = importlib.util.module_from_spec(spec)
            loader.exec_module(csv_loader)
            records_list = csv_loader.load_records(str(csv_path))
            logging.info(f"[CSV_LOAD_SUCCESS] records_list={len(records_list)}件 読み込み")
        except Exception as e:
            logging.error(f"[CSV_LOAD_ERROR] {e}")
            records_list = []

        # ===== 整形済みサマリフォーマッタ準備 =====
        try:
            import importlib.machinery, importlib.util, os as _os
            fmt_loader = importlib.machinery.SourceFileLoader(
                'result_formatter', str(project_root / 'data' / 'result_formatter.py'))
            fmt_spec = importlib.util.spec_from_loader(fmt_loader.name, fmt_loader)
            fmt_mod = importlib.util.module_from_spec(fmt_spec)
            fmt_loader.exec_module(fmt_mod)
            _format_match = fmt_mod.format_match_result
        except Exception:
            def _format_match(r, found, mv):
                # match_test と同じ形式: key タプル全体を表示
                if isinstance(r, dict):
                    rec_str = r.get('key', r)
                else:
                    rec_str = getattr(r, 'key', r)
                return f"found={len(found)}/{mv} {rec_str}"

        # レガシーマッチャー関数をインポート
        from matcher import match_images_and_records, match_images_and_records_normal

        # レガシーマッチャーでマッチング実行（カテゴリ別）
        logging.info("[MATCHER_CALL] match_images_and_records()実行開始")
        results_by_category = match_images_and_records(records_list, image_roles, formatter=_format_match)
        logging.info(f"[MATCHER_OUTPUT] カテゴリ数: {len(results_by_category)}")

        # ===== 整形済みサマリーログ出力 =====

        # Normal matching summary first
        logging.info("=== [Normal Matching Results] ===")
        normal_results = match_images_and_records_normal(records_list, image_roles, formatter=_format_match)
        for img_path, record, found, match_val, formatted in normal_results:
            import os
            logging.info(f"[IMAGE] {os.path.basename(img_path)} | {formatted}")

        # Category grouped
        for cat, ress in results_by_category.items():
            logging.info(f"=== {cat} ===")
            for img_path, record, found, match_val, formatted in ress:
                logging.info(f"[IMAGE] {os.path.basename(img_path)} | {formatted}")
        
        # 結果が空の場合の詳細ダンプ
        if len(results_by_category) == 0:
            logging.error(f"[MATCHER_ERROR] 結果が空です。入力データを再確認:")
            if records_list and isinstance(records_list[0], dict):
                logging.error(f"[MATCHER_ERROR] records_list[0] keys: {list(records_list[0].keys())}")
            else:
                logging.error(f"[MATCHER_ERROR] records_list[0] type: {type(records_list[0]) if records_list else 'EMPTY'}")
            # データをローカルファイルに保存してデバッグ
            import json
            debug_data = {
                'records_list': records_list,
                'image_roles_sample': {k: v for i, (k, v) in enumerate(image_roles.items()) if i < 5}
            }
            with open(project_root / 'logs' / 'matcher_debug_data.json', 'w', encoding='utf-8') as f:
                json.dump(debug_data, f, ensure_ascii=False, indent=2)
            logging.error(f"[MATCHER_ERROR] デバッグデータを logs/matcher_debug_data.json に保存しました")
        
        # 結果の詳細ダンプ
        for category, results in results_by_category.items():
            logging.info(f"[RESULT_CATEGORY] {category}: {len(results)}件")
            for img_path, record, found, match_val, formatted in results:
                if 'RIMG8567' in img_path:
                    logging.info(f"[RESULT_8567] {img_path}: found={found}, record={record}")

        # === カテゴリ別結果を統合 & 特別ロジック適用 ===
        match_results_legacy: dict[str, list] = {}
        for category, results in results_by_category.items():
            for img_path, record, found, match_val, _ in results:
                if img_path not in match_results_legacy:
                    match_results_legacy[img_path] = []
                if record and found:
                    if isinstance(record, dict):
                        rem = record.get('remarks') or record.get('key', ['','','','',''])[4]
                        cr_obj = remarks_to_chain_record.get(rem)
                        if cr_obj:
                            match_results_legacy[img_path].append(cr_obj)
                    else:
                        match_results_legacy[img_path].append(record)

        logging.info(f"[MATCH_RESULTS] マッチした画像数: {len(match_results_legacy)}")

        # DB の画像情報を取得し温度管理写真ロジックへ渡す
        images = self.db_resource_service.get_all_images() if hasattr(self, 'db_resource_service') else []
        match_results = self._apply_temperature_management_logic(match_results_legacy, images)

        # ここまでで例外は記録済みとし、以降の処理で致命的な例外は発生しない想定

        # **エントリー更新処理を削除**（データ上書きを防止）
        
        # DB へ永続化（画像とChainRecordの対応付け）のみ実行
        img_path_to_id = {d['image_path']: d['id'] for d in ImageManager.get_all_images()}
        for img_path, recs in match_results.items():
            img_id = img_path_to_id.get(img_path)
            if img_id is None:
                continue
            rec_list = []
            if isinstance(recs, list):
                rec_list = recs
            elif hasattr(recs, 'chain_records'):
                rec_list = recs.chain_records
            for rec in rec_list:
                # 既存 ChainRecord を DB から取得
                rec_id_rows = [r for r in ChainRecordManager.get_all_chain_records() if r.get('remarks') == getattr(rec, 'remarks', None)]
                if rec_id_rows:
                    rec_id = rec_id_rows[0]['id']
                    ChainRecordManager.assign_chain_record_to_image(img_id, rec_id)
                    logging.info(f"[DB_SAVE] 画像ID:{img_id} にレコードID:{rec_id} ({getattr(rec, 'remarks', 'N/A')}) を割り当て")
                    
        logging.info(f"[MATCH_COMPLETE] マッチング処理完了: 処理画像数={len(match_results)}")
        return match_results

    def full_initialize(self):
        # DB やファイルを毎回リセットすると chain_records が失われるため廃止
        # self.reset_all_resources()
        image_dicts = self.db_resource_service.get_all_images()
        entries = [ImageEntry(image_path=d['image_path']) for d in image_dicts if d.get('image_path')]
        self.set_all_entries(entries)
        self.get_match_results(entries, self.role_mappings, self.remarks_to_chain_record)
        logging.info("[SummaryDataService] full_initialize完了（DB・データ・マッチング・ログ全出力）")

    def _apply_temperature_management_logic(self, match_results_new: dict, images):
        """
        温度管理写真の特別処理を適用する
        品質管理写真では単体マッチングではなく、画像全体から温度管理レコードを収集し、
        到着温度→敷均し温度→初期締固前温度→開放温度の順序で割り当てる
        """
        import logging
        
        # 品質管理写真（温度測定関連）を特定
        temp_images = []
        other_images = []
        
        for img_path, matched_records in match_results_new.items():
            # 画像のロールを確認
            img_roles = []
            for img in images:
                if img.get('image_path') == img_path:
                    img_roles = [b.get('role') for b in img.get('bboxes', [])]
                    break
            
            # 温度測定関連のロールがあるか確認
            is_temp_image = any('thermometer' in role.lower() or '温度' in role for role in img_roles if role)
            
            if is_temp_image:
                temp_images.append(img_path)
            else:
                other_images.append(img_path)
        
        logging.info(f"[TEMP_LOGIC] 温度管理写真: {len(temp_images)}枚, その他: {len(other_images)}枚")
        
        # 結果を既存フォーマットに変換
        match_results: dict[str, list] = {}
        
        # 温度管理写真の特別処理
        if temp_images:
            # temp_records dict keyword->ChainRecord を準備
            all_records = [r for recs in match_results_new.values() for r in recs]
            temp_records = self._extract_temperature_records(all_records)
            temp_match_results = self._assign_temperature_records(temp_images, temp_records)
            match_results.update(temp_match_results)
            logging.info(f"[TEMP_ASSIGNED] 温度管理レコード割り当て完了: {len(temp_match_results)}枚")
        
        # その他の画像は通常処理
        for img_path in other_images:
            matched_records = match_results_new.get(img_path, [])
            if matched_records:
                match_results[img_path] = matched_records
                logging.info(f"[MATCH_SUCCESS] {img_path}: {len(matched_records)}件のレコードマッチ - {[getattr(r, 'remarks', 'N/A') for r in matched_records]}")
            else:
                match_results[img_path] = []
                img_basename = img_path.split('\\')[-1] if '\\' in img_path else img_path.split('/')[-1]
                logging.warning(f"[MATCH_NONE] {img_basename}: マッチなし")
        
        return match_results
    
    def _extract_temperature_records(self, records_list):
        """records_list から温度管理関連 ChainRecord を抽出し dict キーワード→record を返す"""
        temp_keywords = ['到着温度', '敷均し温度', '初期締固前温度', '開放温度']
        mapping = {}
        for rec in records_list:
            for kw in temp_keywords:
                if kw in getattr(rec, 'remarks', ''):
                    mapping[kw] = rec
                    break
        return mapping
    
    def _assign_temperature_records(self, temp_images, temp_records):
        """温度管理写真にレコードを順序立てて割り当て"""
        import logging
        
        # 温度管理レコードの割り当て順序
        assignment_order = []
        n = len(temp_images)
        
        # 基本ロジック: 到着温度3枚→敷均し温度3枚→初期締固前温度3枚→末尾3枚は必ず開放温度
        main_n = max(0, n - 3)
        for i in range(main_n):
            cycle_pos = (i // 3) % 3
            if cycle_pos == 0:
                assignment_order.append('到着温度')
            elif cycle_pos == 1:
                assignment_order.append('敷均し温度')
            else:
                assignment_order.append('初期締固前温度')
        
        # 末尾3枚は開放温度
        for i in range(min(3, n)):
            assignment_order.append('開放温度')
        
        # 実際の割り当て
        results = {}
        for i, img_path in enumerate(temp_images):
            if i < len(assignment_order):
                temp_type = assignment_order[i]
                record = temp_records.get(temp_type)
                if record:
                    results[img_path] = [record]
                    logging.info(f"[TEMP_ASSIGN] {img_path}: {temp_type} ({getattr(record, 'remarks', 'N/A')})")
                else:
                    results[img_path] = []
                    logging.warning(f"[TEMP_MISSING] {img_path}: {temp_type}のレコードが見つかりません")
            else:
                results[img_path] = []
                logging.warning(f"[TEMP_OVERFLOW] {img_path}: 割り当て対象外")
        
        return results