"""
ユーザー辞書管理クラス。
工種、種別、細別などのキャプション辞書を管理します。
"""
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
    """ユーザー辞書管理クラス"""

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

    def __init__(self, dictionary_path=None):
        """初期化

        Args:
            dictionary_path: 辞書ファイルのパス
        """
        super().__init__()
        self.records = []
        self.role_mappings = {}
        self.current_project = None
        self.dictionaries = {}
        self._initialized = False
        self.load_dictionaries()
        if not self._initialized:
            self.save_dictionaries()
            self._initialized = True

        # 保存用ディレクトリを準備
        self._ensure_dictionary_dir()

        # アクティブな辞書の設定を確認
        active_dict_file = os.path.join(
            self._get_dictionary_dir(),
            "active_dictionary.json")
        if os.path.exists(active_dict_file):
            try:
                with open(active_dict_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    active_dict = data.get("active")
                    if active_dict:
                        self.current_project = active_dict
                        logging.info(f"アクティブな辞書を使用します: {active_dict}")
            except Exception as e:
                logging.error(f"アクティブ辞書の読み込みエラー: {e}")

        # --- デバッグ: recordsファイルのパス・存在・件数を出力 ---
        records_file = self._get_records_file()
        print(f"[DEBUG] recordsファイルパス: {records_file}")
        print(f"[DEBUG] recordsファイル存在: {os.path.exists(records_file)}")
        # 辞書をロード
        self.load_dictionaries()
        print(f"[DEBUG] recordsロード件数: {len(self.records)}")
        # --- 起動時に必ずDB登録内容をログ出力 ---
        self.save_dictionaries()

        # 辞書の内容をログに出力
        self._log_dictionary_stats()

    # ----- レコード単位操作（新API） -----

    def add_record(self, record_dict: Dict[str, str]) -> bool:
        """チェーンレコードの追加

        Args:
            record_dict: レコードデータ辞書

        Returns:
            成功したかどうか
        """
        record = ChainRecord.from_dict(record_dict)

        # 重複チェック（正規化して比較）
        for existing in self.records:
            # すべての非空フィールドが一致する場合は重複とみなす
            if (normalize(existing.category) == normalize(record.category) and
                normalize(existing.type) == normalize(record.type) and
                normalize(existing.subtype) == normalize(record.subtype) and
                normalize(existing.remarks) == normalize(record.remarks) and
                normalize(existing.station) == normalize(record.station) and
                    normalize(existing.control) == normalize(record.control)):
                return False

        # レコード追加
        self.records.append(record)

        # 個別辞書も更新（後方互換性のため）
        self._update_individual_dictionaries()

        # 変更を通知
        self.dictionary_changed.emit()

        return True

    def update_record(self, index: int, record_dict: Dict[str, str]) -> bool:
        """チェーンレコードの更新

        Args:
            index: 更新するレコードのインデックス
            record_dict: 新しいレコードデータ辞書

        Returns:
            成功したかどうか
        """
        if not (0 <= index < len(self.records)):
            logging.error(f"無効なレコードインデックス: {index}")
            return False

        # レコード更新
        self.records[index] = ChainRecord.from_dict(record_dict)

        # 個別辞書も更新（後方互換性のため）
        self._update_individual_dictionaries()

        # 変更を通知
        self.dictionary_changed.emit()

        return True

    def delete_record(self, index: int) -> bool:
        """チェーンレコードの削除

        Args:
            index: 削除するレコードのインデックス

        Returns:
            成功したかどうか
        """
        if not (0 <= index < len(self.records)):
            logging.error(f"無効なレコードインデックス: {index}")
            return False

        # レコード削除
        del self.records[index]

        # 個別辞書も更新（後方互換性のため）
        self._update_individual_dictionaries()

        # 変更を通知
        self.dictionary_changed.emit()

        return True

    def insert_record(self, index: int, record_dict: Dict[str, str]) -> bool:
        """指定した位置にレコードを挿入

        Args:
            index: 挿入位置のインデックス
            record_dict: レコードデータ辞書

        Returns:
            挿入に成功した場合はTrue、失敗した場合はFalse
        """
        if not (0 <= index <= len(self.records)):
            logging.error(f"無効なレコードインデックス: {index}")
            return False

        record = ChainRecord.from_dict(record_dict)

        # レコードを挿入
        self.records.insert(index, record)

        # 個別辞書も更新（後方互換性のため）
        self._update_individual_dictionaries()

        # 変更を通知
        self.dictionary_changed.emit()

        return True

    # ----- 従来のAPI（後方互換性） -----

    def get_entries(self, dict_type: str) -> List[str]:
        """特定タイプの辞書エントリリストを取得

        Args:
            dict_type: 辞書タイプ（CATEGORY, TYPE など）

        Returns:
            エントリのリスト
        """
        if dict_type in self.dictionaries:
            return self.dictionaries[dict_type]
        return []

    def add_entry(self, dict_type: str, entry: str) -> bool:
        """辞書エントリを追加

        Args:
            dict_type: 辞書タイプ
            entry: 追加するエントリ

        Returns:
            成功したかどうか
        """
        if dict_type not in self.dictionaries:
            logging.error(f"無効な辞書タイプ: {dict_type}")
            return False

        # 重複チェック
        if entry in self.dictionaries[dict_type]:
            return False

        # 追加
        self.dictionaries[dict_type].append(entry)
        self.dictionaries[dict_type].sort()  # ソート

        # レコードにも反映
        self._update_records_from_dictionaries()

        # 変更を通知
        self.dictionary_changed.emit()

        return True

    def remove_entry(self, dict_type: str, entry: str) -> bool:
        """辞書エントリを削除

        Args:
            dict_type: 辞書タイプ
            entry: 削除するエントリ

        Returns:
            成功したかどうか
        """
        if dict_type not in self.dictionaries:
            logging.error(f"無効な辞書タイプ: {dict_type}")
            return False

        if entry not in self.dictionaries[dict_type]:
            return False

        # 削除
        self.dictionaries[dict_type].remove(entry)

        # レコードにも反映
        self._update_records_from_dictionaries()

        # 変更を通知
        self.dictionary_changed.emit()

        return True

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
        if dict_type not in self.dictionaries:
            logging.error(f"無効な辞書タイプ: {dict_type}")
            return False

        # 古いエントリを削除し、新しいエントリを追加
        if old_entry in self.dictionaries[dict_type]:
            self.dictionaries[dict_type].remove(old_entry)
            self.dictionaries[dict_type].append(new_entry)
            self.dictionaries[dict_type].sort()  # ソート

            # レコードにも反映
            self._update_records_from_dictionaries()

            # 変更を通知
            self.dictionary_changed.emit()

            return True

        return False

    def load_dictionaries(self) -> bool:
        """
        DBからChainRecord/ロールマッピングをロードし、self.records等にセットする。role_mapping.jsonも参照。
        """
        import os
        log_path = 'logs/A_dictionary_load.log'
        def log(msg, obj=None):
            with open(log_path, 'w', encoding='utf-8') as f:
                if obj is not None:
                    f.write(msg + ' ' + json.dumps(obj, ensure_ascii=False) + '\n')
                else:
                    f.write(msg + '\n')
        try:
            self.records = [ChainRecord.from_dict(r) for r in ChainRecordManager.get_all_chain_records()]
            # --- ロールマッピングをDB＋JSONから統合ロード ---
            db_role_mappings = {row['role_name']: json.loads(row['mapping_json']) for row in RoleMappingManager.get_all_role_mappings()}
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
            ChainRecordManager.add_chain_record(
                location=getattr(r, 'location', None),
                controls=getattr(r, 'controls', []),
                photo_category=getattr(r, 'photo_category', None),
                work_category=getattr(r, 'work_category', None),
                type_=getattr(r, 'type', None),
                subtype=getattr(r, 'subtype', None),
                remarks=getattr(r, 'remarks', None),
                extra_json=json.dumps(getattr(r, 'extra', None), ensure_ascii=False) if getattr(r, 'extra', None) else None
            )
        for role_name, mapping in self.role_mappings.items():
            RoleMappingManager.add_or_update_role_mapping(role_name, json.dumps(mapping, ensure_ascii=False))
        # --- ここで一度だけ全リストをログ出力（要素ごとに改行） ---
        log_path = 'logs/A_dictionary_register.log'
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
        """現在の工事名を設定し、辞書を切り替える

        Args:
            project_name: 工事名
        """
        if not project_name:
            logging.error("プロジェクト名が指定されていません")
            return

        # 同じ名前なら何もしない
        if project_name == self.current_project:
            logging.info(f"既に '{project_name}' が設定されています")
            return

        # 現在の辞書を保存
        self.save_dictionaries()

        # 辞書ファイルの存在を確認
        dict_dir = self._get_dictionary_dir()
        custom_dir = os.path.join(dict_dir, "custom")

        # 候補となるファイルパスリスト
        dict_files = [
            # 通常の辞書ファイル
            os.path.join(dict_dir, f"{project_name}_dictionary.json"),
            # カスタム辞書
            os.path.join(custom_dir, f"{project_name}.json"),
            # レガシーパス
            os.path.join(dict_dir, project_name, "dictionary.json")
        ]

        # いずれかのファイルが存在するか確認
        exists = any(os.path.exists(path) for path in dict_files)

        if not exists:
            logging.warning(f"プロジェクト '{project_name}' の辞書ファイルが見つかりません")
            # ただし、project_nameがdefaultの場合は常に許可
            if project_name != "default":
                return

        # 工事名を変更
        logging.info(f"辞書を切り替えました: {self.current_project} -> {project_name}")
        self.current_project = project_name

        # 新しい工事の辞書をロード
        self.load_dictionaries()

        # 辞書の内容をログ出力
        self._log_dictionary_stats()

    def reload_dictionaries(self):
        """辞書をリロード"""
        # 現在の辞書を保存
        self.save_dictionaries()

        # 辞書を再ロード
        self.load_dictionaries()

        # 辞書の内容をログ出力
        self._log_dictionary_stats()

        # 変更を通知
        self.dictionary_changed.emit()

    def _log_dictionary_stats(self):
        """辞書の統計情報をログに出力"""
        logging.info(f"辞書ファイル: {self._get_dictionary_file()}")
        logging.info(f"レコードファイル: {self._get_records_file()}")
        logging.info(f"レコード数: {len(self.records)}")

        # 各タイプの項目数を出力
        for dict_type, entries in self.dictionaries.items():
            logging.info(f"  {dict_type} 項目数: {len(entries)}")

    # ----- マッチング機能 -----

    def match_text_with_dictionary(self, text: str) -> Dict[str, str]:
        """OCRテキストと辞書のマッチング（精度改善版）

        Args:
            text: OCRで検出されたテキスト

        Returns:
            マッチング結果（辞書タイプ: マッチしたエントリ）
        """
        if not text or not self.records:
            return {}

        # 1. キーワードベースのマッチング
        keyword_results = self._keyword_match(text)
        keyword_score = 0
        if keyword_results:
            # キーワードマッチのスコアを計算（マッチ数合計）
            keyword_score = len(keyword_results)

        # 2. ファジーマッチング（OCRテキストの各行・各フィールドで最大スコア）
        best_record = None
        best_score = 0
        best_record_dict = None
        ocr_lines = [normalize(line) for line in text.splitlines() if line.strip()]
        for record in self.records:
            record_dict = record.to_dict()
            for field, value in record_dict.items():
                if not value:
                    continue
                rec_val = normalize(str(value))
                for ocr_line in ocr_lines:
                    score = fuzz.partial_ratio(rec_val, ocr_line)
                    if score > best_score:
                        best_score = score
                        best_record = record
                        best_record_dict = record_dict
        # 3. 完全一致（OCRテキストに完全一致するフィールドがあれば最優先）
        for record in self.records:
            record_dict = record.to_dict()
            for field, value in record_dict.items():
                if not value:
                    continue
                if str(value) in text:
                    # 完全一致があれば即返す
                    return {k: v for k, v in record_dict.items() if v}

        # 4. 最良スコアのものを返す（キーワードマッチとファジーマッチを比較）
        if best_score >= self.MATCH_THRESHOLD:
            return {k: v for k, v in best_record_dict.items() if v}
        elif keyword_results:
            return keyword_results
        else:
            # どれも該当しない場合は空
            return {}

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

    def _best_match(self, text: str) -> tuple[Optional[ChainRecord], float]:
        """最も良いマッチのレコードとスコアを返す

        Args:
            text: OCRで検出されたテキスト

        Returns:
            (最良マッチレコード, スコア) のタプル
        """
        if not text or not self.records:
            return None, 0

        # テキストを正規化
        text_norm = normalize(text)

        best_record = None
        best_score = 0

        for record in self.records:
            # 各レコードのトークン（正規化済み）とマッチング
            record_tokens = record.tokens()

            if not record_tokens:
                continue

            # 最も高いスコアを保持
            score = max(
                fuzz.partial_ratio(text_norm, token)
                for token in record_tokens
            )

            if score > best_score:
                best_record = record
                best_score = score

        return best_record, best_score

    def _legacy_match_text(self, text: str) -> Dict[str, str]:
        """従来の完全一致マッチング（フォールバック用）

        Args:
            text: OCRで検出されたテキスト

        Returns:
            マッチング結果（辞書タイプ: マッチしたエントリ）
        """
        result = {}

        # 各辞書タイプに対して
        for dict_type, entries in self.dictionaries.items():
            # 辞書の各エントリに対して
            for entry in entries:
                # テキストに含まれているかチェック
                if entry and entry in text:
                    # マッチしたら結果に追加
                    result[dict_type] = entry
                    break

        return result

    def _extract_keywords(self, text: str) -> List[str]:
        """テキストからキーワードを抽出

        Args:
            text: 解析するテキスト

        Returns:
            抽出されたキーワードのリスト
        """
        if not text:
            return []

        keywords = []

        # まず特殊なパターン（H1=50、RM-40のような識別子）を抽出
        special_patterns = re.findall(
            r'([A-Za-z]+\d*[\-=]+\d+|[A-Za-z]+\d*\-[A-Za-z]+\d*)', text)
        keywords.extend(special_patterns)

        # 残りのテキストをスペース、カンマ、括弧などで分割
        # 特殊パターンが抽出されたテキストを一時的に置換して分割
        temp_text = text
        for pattern in special_patterns:
            temp_text = temp_text.replace(pattern, "")

        words = re.split(r'[\s\.,;:()\[\]]+', temp_text)

        for word in words:
            if not word or len(word) < 2:  # 2文字未満は無視
                continue

            # 通常の単語を追加
            keywords.append(word)

        # 重複を削除して返す
        return list(set(keywords))

    def _keyword_match(self, text: str) -> Dict[str, str]:
        """キーワードベースのマッチング

        テキストから抽出したキーワードと辞書レコードのキーワードが一致するかを調べる

        Args:
            text: OCRで検出されたテキスト

        Returns:
            マッチング結果（辞書タイプ: マッチしたエントリ）
        """
        if not text or not self.records:
            return {}

        # テキストからキーワードを抽出
        text_keywords = self._extract_keywords(text)
        if not text_keywords:
            return {}

        # テキストキーワードを正規化（比較のため）
        text_keywords_norm = {normalize(kw) for kw in text_keywords}

        result = {}
        best_matches = {}  # 各フィールドタイプごとの最良マッチを保存

        # 各レコードを調査
        for record in self.records:
            record_dict = record.to_dict()
            record_keywords = record.keywords()

            # レコードのキーワードを正規化
            record_keywords_norm = {normalize(kw) for kw in record_keywords}

            # レコードの各フィールドを調査
            for dict_type, value in record_dict.items():
                if not value:
                    continue

                # テキストキーワードとレコードキーワードの重複を検出
                matches = text_keywords_norm.intersection(record_keywords_norm)

                # 一致があればそのフィールドを結果に追加
                if matches:
                    # より多くのキーワードがマッチする場合、または初めてのマッチングの場合
                    match_count = len(matches)
                    if dict_type not in best_matches or match_count > best_matches[dict_type][0]:
                        best_matches[dict_type] = (match_count, value)

        # 最良マッチを結果に追加
        for dict_type, (_, value) in best_matches.items():
            result[dict_type] = value

        return result

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
        if not ocr_text or not self.records:
            return []
        if fields is None:
            fields = [
                "category",
                "type",
                "subtype",
                "remarks",
                "station",
                "control"]
        ocr_lines = [normalize(line)
                     for line in ocr_text.splitlines() if line.strip()]
        matches = []
        for idx, record in enumerate(self.records):
            best_score = 0
            best_line = ""
            best_field = ""
            for field in fields:
                field_value = normalize(getattr(record, field, ""))
                if not field_value:
                    continue
                for ocr_line in ocr_lines:
                    score = fuzz.partial_ratio(field_value, ocr_line)
                    if score > best_score:
                        best_score = score
                        best_line = ocr_line
                        best_field = field
            if best_score >= threshold:
                matches.append({
                    "record_index": idx,
                    "record": record,
                    "score": best_score,
                    "matched_field": best_field,
                    "ocr_line": best_line
                })
        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches[:top_n]

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
