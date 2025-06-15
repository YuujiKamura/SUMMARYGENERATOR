"""
ユーザー辞書管理クラス。
工種、種別、細別などのキャプション辞書を管理します。
"""
# flake8: noqa
from __future__ import annotations
import json
import os
import logging
import re
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

from PyQt6.QtCore import QObject, pyqtSignal
from src.utils.path_manager import path_manager
from src.utils.chain_record_utils import ChainRecord, load_chain_records
from src.db_manager import ChainRecordManager, RoleMappingManager
from src.services.dictionary_persistence_service import DictionaryPersistenceService
from src.services.dictionary_record_service import DictionaryRecordService
from src.services.dictionary_entry_service import DictionaryEntryService
from src.services.dictionary_matching_service import DictionaryMatchingService
# 類似度計算用ライブラリ
try:
    from rapidfuzz import fuzz
except ImportError:
    logging.warning(
        "rapidfuzz がインストールされていません。pip install rapidfuzz でインストールしてください。マッチング精度が低下します。")
    # フォールバック用の簡易実装

    class fuzz:
        @staticmethod
        def ratio(s1: str, s2: str) -> float:
            """文字列の類似度を計算（0-100）"""
            if not s1 or not s2:
                return 0
            return 100 if s1 == s2 else 50

        @staticmethod
        def partial_ratio(s1: str, s2: str) -> float:
            """部分文字列の類似度を計算（0-100）"""
            if not s1 or not s2:
                return 0
            if s1 in s2 or s2 in s1:
                return 90
            return 0


# 文字列正規化用の変換テーブル（全角→半角、空白削除）
NORMALIZE_TABLE = str.maketrans({
    # 全角スペース、半角スペース、タブを削除
    '　': None, ' ': None, '\t': None,
    # 全角カナを半角に変換（必要に応じて拡張）
    'ａ': 'a', 'ｂ': 'b', 'ｃ': 'c', 'ｄ': 'd', 'ｅ': 'e',
    'ｆ': 'f', 'ｇ': 'g', 'ｈ': 'h', 'ｉ': 'i', 'ｊ': 'j',
    'ｋ': 'k', 'ｌ': 'l', 'ｍ': 'm', 'ｎ': 'n', 'ｏ': 'o',
    'ｐ': 'p', 'ｑ': 'q', 'ｒ': 'r', 'ｓ': 's', 'ｔ': 't',
    'ｕ': 'u', 'ｖ': 'v', 'ｗ': 'w', 'ｘ': 'x', 'ｙ': 'y', 'ｚ': 'z',
    'Ａ': 'A', 'Ｂ': 'B', 'Ｃ': 'C', 'Ｄ': 'D', 'Ｅ': 'E',
    'Ｆ': 'F', 'Ｇ': 'G', 'Ｈ': 'H', 'Ｉ': 'I', 'Ｊ': 'J',
    'Ｋ': 'K', 'Ｌ': 'L', 'Ｍ': 'M', 'Ｎ': 'N', 'Ｏ': 'O',
    'Ｐ': 'P', 'Ｑ': 'Q', 'Ｒ': 'R', 'Ｓ': 'S', 'Ｔ': 'T',
    'Ｕ': 'U', 'Ｖ': 'V', 'Ｗ': 'W', 'Ｘ': 'X', 'Ｙ': 'Y', 'Ｚ': 'Z',
    '０': '0', '１': '1', '２': '2', '３': '3', '４': '4',
    '５': '5', '６': '6', '７': '7', '８': '8', '９': '9',
})

# 追加の文字列正規化用の変換テーブル（機能拡張用）
EXTRA_NORMALIZE_TABLE = str.maketrans({})


def normalize(text: str) -> str:
    """文字列を正規化する（全角→半角、空白削除、小文字化）

    Args:
        text: 正規化する文字列

    Returns:
        正規化された文字列
    """
    if not text:
        return ""

    # 全角→半角、空白削除
    normalized = text.translate(NORMALIZE_TABLE)

    # 全角文字を半角に変換（残り）
    normalized = re.sub(r'[Ａ-Ｚａ-ｚ０-９]',
                        lambda x: chr(ord(x.group(0)) - 0xFEE0),
                        normalized)

    # 小文字化して返す
    return normalized.lower()


# 正規表現パターン - 特殊な識別子（アルファベットと数字やハイフンの組み合わせ）を検出
KEYWORD_PATTERN = re.compile(
    r'([A-Za-z]+[\-\d=]+\d*|[A-Za-z]+[^\s\.,;:()]*[\d]+)')


class DictionaryManager(QObject):
    """ユーザー辞書管理クラス（ファサード）"""

    # シグナル定義
    dictionary_changed = pyqtSignal()  # 辞書変更時に発火

    # 辞書タイプ定数
    CATEGORY = "category"         # 工種
    TYPE = "type"                 # 種別
    SUBTYPE = "subtype"           # 細別
    REMARKS = "remarks"           # 備考
    STATION = "station"           # 測点
    CONTROL_VALUES = "control"    # 管理値（設計値・実測値）

    # 類似度マッチングの閾値（0-100）
    MATCH_THRESHOLD = 70

    def __init__(self, db_path):
        """初期化
        """
        super().__init__()
        self.db_path = db_path
        self.records = []  # recordsを必ず初期化
        self.role_mappings = {}  # role_mappingsも初期化
        # サービス群を集約（全てにdb_pathを渡す）
        self.persistence = DictionaryPersistenceService(self, db_path)
        self.record_service = DictionaryRecordService(self, db_path)
        self.entry_service = DictionaryEntryService(self, db_path)
        self.matching_service = DictionaryMatchingService(self, db_path)
        # DBベースで初期化
        self.persistence.load_dictionaries()
        self.persistence.save_dictionaries()

        # ---- CSV から最新レコード／ロールマッピングを読み込む ----
        try:
            from src.utils.csv_records_loader import load_records_and_roles_csv
            csv_path = path_manager.records_and_roles_csv
            if csv_path.exists():
                csv_records, csv_mappings = load_records_and_roles_csv(csv_path)
                if csv_mappings:
                    # 新しいChainRecordをDBへ登録（roles情報含むextra_json）
                    from src.db_manager import ChainRecordManager
                    import json as _json
                    for rec in csv_records:
                        ChainRecordManager.add_chain_record(
                            location=rec.location,
                            controls=rec.controls,
                            photo_category=rec.photo_category,
                            work_category=rec.work_category,
                            type_=rec.type,
                            subtype=rec.subtype,
                            remarks=rec.remarks,
                            extra_json=_json.dumps(rec.extra, ensure_ascii=False),
                        )

                    for remarks, mp in csv_mappings.items():
                        RoleMappingManager.add_or_update_role_mapping(
                            remarks,
                            _json.dumps(mp, ensure_ascii=False),
                        )
                    # 挿入後にDB内容でself.records / self.role_mappings を再取得
                    self.records = [
                        ChainRecord.from_dict(r)
                        for r in ChainRecordManager.get_all_chain_records()
                    ]
                    self.role_mappings = {
                        row['role_name']: json.loads(row['mapping_json'])
                        for row in RoleMappingManager.get_all_role_mappings()
                    }
        except Exception as e:
            logging.warning("CSVレコード／ロールマッピング読込に失敗: %s", e)

        self._log_dictionary_stats()

    # ----- レコード単位操作（新API） -----

    def add_record(self, record_dict: Dict[str, str]) -> bool:
        """チェーンレコードの追加

        Args:
            record_dict: レコードデータ辞書

        Returns:
            成功したかどうか
        """
        return self.record_service.add_record(record_dict)

    def update_record(self, index: int, record_dict: Dict[str, str]) -> bool:
        """チェーンレコードの更新

        Args:
            index: 更新するレコードのインデックス
            record_dict: 新しいレコードデータ辞書

        Returns:
            成功したかどうか
        """
        return self.record_service.update_record(index, record_dict)

    def delete_record(self, index: int) -> bool:
        """チェーンレコードの削除

        Args:
            index: 削除するレコードのインデックス

        Returns:
            成功したかどうか
        """
        return self.record_service.delete_record(index)

    def insert_record(self, index: int, record_dict: Dict[str, str]) -> bool:
        """指定した位置にレコードを挿入

        Args:
            index: 挿入位置のインデックス
            record_dict: レコードデータ辞書

        Returns:
            挿入に成功した場合はTrue、失敗した場合はFalse
        """
        return self.record_service.insert_record(index, record_dict)

    # ----- 従来のAPI（後方互換性） -----

    def get_entries(self, dict_type: str) -> List[str]:
        """特定タイプの辞書エントリリストを取得

        Args:
            dict_type: 辞書タイプ（CATEGORY, TYPE など）

        Returns:
            エントリのリスト
        """
        return self.entry_service.get_entries(dict_type)

    def add_entry(self, dict_type: str, entry: str) -> bool:
        """辞書エントリを追加

        Args:
            dict_type: 辞書タイプ
            entry: 追加するエントリ

        Returns:
            成功したかどうか
        """
        return self.entry_service.add_entry(dict_type, entry)

    def remove_entry(self, dict_type: str, entry: str) -> bool:
        """辞書エントリを削除

        Args:
            dict_type: 辞書タイプ
            entry: 削除するエントリ

        Returns:
            成功したかどうか
        """
        return self.entry_service.remove_entry(dict_type, entry)

    def update_entry(
            self,
            dict_type: str,
            old_entry: str,
            new_entry: str) -> bool:
        """辞書エントリを更新

        Args:
            dict_type: 辞書タイプ
            old_entry: 更新前のエントリ
            new_entry: 更新後のエントリ

        Returns:
            成功したかどうか
        """
        return self.entry_service.update_entry(dict_type, old_entry, new_entry)

    def load_dictionaries(self) -> bool:
        """
        DBからChainRecord/ロールマッピングをロードし、self.records等にセットする。role_mapping.jsonも参照。
        """
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, 'A_dictionary_load.log')
        def log(msg, obj=None):
            with open(log_path, 'w', encoding='utf-8') as f:
                if obj is not None:
                    f.write(msg + ' ' + json.dumps(obj, ensure_ascii=False) + '\n')
                else:
                    f.write(msg + '\n')
        try:
            self.records = [ChainRecord.from_dict(r) for r in ChainRecordManager.get_all_chain_records()]
            # --- ロールマッピングをDB＋JSONから統合ロード（DB優先） ---
            db_role_mappings = {}
            for row in RoleMappingManager.get_all_role_mappings():
                role_name = row.get('role_name')
                mapping_json = row.get('mapping_json')
                if role_name and mapping_json:
                    db_role_mappings[role_name] = json.loads(mapping_json)
            # JSONファイルも（あれば）ロード
            json_role_mapping_path = os.path.join(os.path.dirname(__file__), '../data/role_mapping.json')
            file_role_mappings = {}
            if os.path.exists(json_role_mapping_path):
                with open(json_role_mapping_path, 'r', encoding='utf-8') as f:
                    file_role_mappings = json.load(f)
            # DB優先でマージ
            self.role_mappings = {**file_role_mappings, **db_role_mappings}
            log('A_CHAINRECORD_LOAD', {'count': len(self.records), 'records': [
                {
                    'photo_category': getattr(r, 'photo_category', None),
                    'work_category': getattr(r, 'work_category', None),
                    'type': getattr(r, 'type', None),
                    'subtype': getattr(r, 'subtype', None),
                    'remarks': getattr(r, 'remarks', None)
                }
                for r in self.records[:10]
            ]})
            log('A_ROLEMAPPING_LOAD', {'count': len(self.role_mappings), 'role_names': list(self.role_mappings.keys())[:10]})
            return True
        except Exception as e:
            log('A_DICTIONARY_LOAD_ERROR', {'error': str(e)})
            return False

    def save_dictionaries(self) -> bool:
        """
        DBへChainRecord/ロールマッピングを保存する（既存レコードは全削除→再登録）。
        保存完了後、全ChainRecord/RoleMappingリストを一度だけログに出力。
        """
        # 既存レコード全削除（必要に応じて実装）
        # for r in self.records:
        #     ChainRecordManager.delete_chain_record(r.remarks)
        for r in self.records:
            import json as _json
            ChainRecordManager.add_chain_record(
                location=r.location,
                controls=r.controls,
                photo_category=r.photo_category,
                work_category=r.work_category,
                type_=r.type,
                subtype=r.subtype,
                remarks=r.remarks,
                extra_json=_json.dumps(r.extra, ensure_ascii=False)
            )
        for role_name, mapping in self.role_mappings.items():
            RoleMappingManager.add_or_update_role_mapping(role_name, json.dumps(mapping, ensure_ascii=False))
        # --- ここで一度だけ全リストをログ出力（要素ごとに改行） ---
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, 'A_dictionary_register.log')
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write('A_CHAINRECORD_REGISTER_LIST [\n')
            for r in self.records:
                f.write(json.dumps({
                    'photo_category': getattr(r, 'photo_category', None),
                    'work_category': getattr(r, 'work_category', None),
                    'type': getattr(r, 'type', None),
                    'subtype': getattr(r, 'subtype', None),
                    'remarks': getattr(r, 'remarks', None)
                }, ensure_ascii=False) + ',\n')
            f.write(']\n')
            f.write('A_ROLEMAPPING_REGISTER_LIST [\n')
            for k, v in self.role_mappings.items():
                f.write(json.dumps({'role_name': k, 'mapping': v}, ensure_ascii=False) + ',\n')
            f.write(']\n')
        return True

    def set_project(self, project_name: str):
        """現在の工事名を設定し、辞書を切り替える"""
        if not project_name:
            logging.error("プロジェクト名が指定されていません")
            return
        if project_name == getattr(self, 'current_project', None):
            logging.info(f"既に '{project_name}' が設定されています")
            return
        # 現在の辞書を保存
        self.persistence.save_dictionaries()
        dict_dir = self._get_dictionary_dir()
        custom_dir = os.path.join(dict_dir, "custom")
        dict_files = [
            os.path.join(dict_dir, f"{project_name}_dictionary.json"),
            os.path.join(custom_dir, f"{project_name}.json"),
            os.path.join(dict_dir, project_name, "dictionary.json")
        ]
        exists = any(os.path.exists(path) for path in dict_files)
        if not exists and project_name != "default":
            logging.warning(f"プロジェクト '{project_name}' の辞書ファイルが見つかりません")
            return
        logging.info(f"辞書を切り替えました: {getattr(self, 'current_project', None)} -> {project_name}")
        self.current_project = project_name
        self.persistence.load_dictionaries()
        self._log_dictionary_stats()

    def reload_dictionaries(self):
        """辞書をリロード"""
        self.persistence.save_dictionaries()
        self.persistence.load_dictionaries()
        self._log_dictionary_stats()
        self.dictionary_changed.emit()

    def _log_dictionary_stats(self):
        """辞書の統計情報をログに出力"""
        logging.info(f"辞書ファイル: {self._get_dictionary_file()}")
        logging.info(f"レコードファイル: {self._get_records_file()}")
        logging.info(f"レコード数: {len(getattr(self, 'records', []))}")
        # 各タイプの項目数を出力
        dicts = getattr(self, 'dictionaries', {})
        for dict_type, entries in dicts.items():
            logging.info(f"  {dict_type} 項目数: {len(entries)}")

    # ----- マッチング機能 -----

    def match_text_with_dictionary(self, text: str) -> Dict[str, str]:
        """OCRテキストと辞書のマッチング（精度改善版）

        Args:
            text: OCRで検出されたテキスト

        Returns:
            マッチング結果（辞書タイプ: マッチしたエントリ）
        """
        return self.matching_service.match_text_with_dictionary(text)

    def record_has_keywords(self, record, keywords) -> bool:
        """
        レコードのphoto_categoryにkeywordsのいずれかが含まれる場合Trueを返す
        Args:
            record: チェック対象のレコード
            keywords: 検索キーワード（リスト）
        Returns:
            bool
        """
        photo_category = getattr(record, "photo_category", "") or ""
        return any(kw in photo_category for kw in keywords)

    def match_roles_records_normal(self, roles, role_mapping, records) -> list:
        """
        recordsのphoto_categoryに「出来形」や「出来形管理」などのキーワードが含まれるレコードのみ返す。
        """
        dekigata_keywords = ["出来形", "出来形管理"]
        return [rec for rec in records if self.record_has_keywords(rec, dekigata_keywords)]

    def is_dekigata_related_record(self, record) -> bool:
        """
        レコードのphoto_categoryに「出来形」や「出来形管理」などのキーワードが含まれる場合Trueを返す
        """
        dekigata_keywords = ["出来形", "出来形管理"]
        return self.record_has_keywords(record, dekigata_keywords)

    def is_hinshitsu_related_record(self, record) -> bool:
        """
        レコードのphoto_categoryに「品質管理」などのキーワードが含まれる場合Trueを返す
        """
        hinshitsu_keywords = ["品質管理"]
        return self.record_has_keywords(record, hinshitsu_keywords)

    def _best_match(self, text: str):
        """最も良いマッチのレコードとスコアを返す

        Args:
            text: OCRで検出されたテキスト

        Returns:
            (最良マッチレコード, スコア) のタプル
        """
        return self.matching_service._best_match(text)

    def _legacy_match_text(self, text: str) -> dict:
        """従来の完全一致マッチング（フォールバック用）

        Args:
            text: OCRで検出されたテキスト

        Returns:
            マッチング結果（辞書タイプ: マッチしたエントリ）
        """
        return self.matching_service._legacy_match_text(text)

    def _extract_keywords(self, text: str) -> list:
        """テキストからキーワードを抽出

        Args:
            text: 解析するテキスト

        Returns:
            抽出されたキーワードのリスト
        """
        return self.matching_service._extract_keywords(text)

    def _keyword_match(self, text: str) -> dict:
        """キーワードベースのマッチング

        テキストから抽出したキーワードと辞書レコードのキーワードが一致するかを調べる

        Args:
            text: OCRで検出されたテキスト

        Returns:
            マッチング結果（辞書タイプ: マッチしたエントリ）
        """
        return self.matching_service._keyword_match(text)

    def find_best_matches(
            self,
            ocr_text: str,
            fields=None,
            top_n=3,
            threshold=70):
        """
        OCRテキストと全レコード・全フィールド・全OCR行の類似度を計算し、
        スコア付きで上位N件の候補リストを返す。
        Args:
            ocr_text: OCRで検出されたテキスト
            fields: チェック対象フィールド（Noneなら全フィールド）
            top_n: 上位何件返すか
            threshold: 類似度スコアのしきい値（0-100）
        Returns:
            List[dict]:
                {
                    'record_index': int,
                    'record': DictRecord,
                    'score': float,
                    'matched_field': str,
                    'ocr_line': str
                }
        """
        return self.matching_service.find_best_matches(ocr_text, fields, top_n, threshold)

    # ----- ロールマッピング逆引きマッチングAPI（新設） -----

    def match_remarks_by_roles(self, roles: list[str], match_mode: str = "") -> list[str]:
        """
        画像のrolesリストから、role_mappings（DB/JSON）を逆引きして該当remarks（工種名）を返す。
        match_mode: "all"なら全て含む場合のみ、"any"なら1つでも含む場合。
        指定なしならrole_mapping側のmatch条件を使う。
        Returns: マッチしたremarks（工種名）のリスト
        """
        if not roles or not self.role_mappings:
            return []
        matched_remarks = []
        roles_set = set(roles)
        for remarks, mapping in self.role_mappings.items():
            mapping_roles = set(mapping.get("roles", []))
            match = match_mode or mapping.get("match", "all")
            if not mapping_roles:
                continue
            if match == "all":
                if mapping_roles.issubset(roles_set):
                    matched_remarks.append(remarks)
            else:  # "any"
                if mapping_roles & roles_set:
                    matched_remarks.append(remarks)
        return matched_remarks

    def get_role_mapping_entries(self) -> list[dict]:
        """
        role_mappingsの全エントリを[{remarks, roles, match}]形式で返す（DB/JSON両対応）
        """
        result = []
        for remarks, mapping in self.role_mappings.items():
            result.append({
                "remarks": remarks,
                "roles": mapping.get("roles", []),
                "match": mapping.get("match", "all")
            })
        return result

    # ----- 個別辞書アクセス用プロパティ -----
    @property
    def dictionaries(self) -> dict:
        """個別辞書（型: dict[str, list]）を取得。なければ空dictを返す"""
        return getattr(self, '_dictionaries', {})

    @dictionaries.setter
    def dictionaries(self, value: dict):
        self._dictionaries = value

    # ----- 内部ヘルパーメソッド -----

    def _update_individual_dictionaries(self):
        """レコードリストから個別辞書を更新"""
        # 辞書をクリア
        for dict_type in self.dictionaries:
            self.dictionaries[dict_type] = []

        # レコードから辞書を生成
        for record in self.records:
            record_dict = record.to_dict()

            for dict_type, value in record_dict.items():
                if dict_type in self.dictionaries:
                    if value and value not in self.dictionaries[dict_type]:
                        self.dictionaries[dict_type].append(value)
        # 各辞書をソート
        for dict_type in self.dictionaries:
            self.dictionaries[dict_type].sort()

    def _update_records_from_dictionaries(self):
        """古い形式の個別辞書からレコードを生成（必要に応じて）"""
        # 既存レコードがある場合は操作しない
        if self.records:
            return

        # 各タイプの辞書から一時的なレコードセットを作成
        for category in self.dictionaries.get(self.CATEGORY, []):
            for type_value in self.dictionaries.get(self.TYPE, []):
                record = ChainRecord(remarks="", photo_category=category, type=type_value)
                self.records.append(record)

    def _get_dictionary_file(self) -> str:
        """現在の工事用の辞書ファイルパスを取得

        Returns:
            辞書ファイルのパス
        """
        # path_manager経由で取得
        return str(path_manager.default_records)

    def _get_records_file(self) -> str:
        """現在の工事用のレコードファイルパスを取得

        Returns:
            レコードファイルのパス
        """
        # path_manager経由で取得
        return str(path_manager.default_records)

    def _get_dictionary_dir(self) -> str:
        """辞書ディレクトリのパスを取得

        Returns:
            辞書ディレクトリのパス
        """
        # path_manager経由で取得
        return str(path_manager.src_dir)

    def _ensure_dictionary_dir(self):
        """辞書ディレクトリが存在することを確認し、なければ作成"""
        dict_dir = self._get_dictionary_dir()
        os.makedirs(dict_dir, exist_ok=True)
