import logging
logger = logging.getLogger(__name__)

class DictionaryMatchingService:
    def __init__(self, manager, db_path=None):
        self.manager = manager
        self.db_path = db_path
    def match_text_with_dictionary(self, text):
        # ...existing code from DictionaryManager.match_text_with_dictionary...
        pass
    def find_best_matches(self, ocr_text, fields=None, top_n=3, threshold=70):
        # ...existing code from DictionaryManager.find_best_matches...
        pass
    def record_has_keywords(self, record, keywords):
        # ...existing code from DictionaryManager.record_has_keywords...
        pass
    def match_roles_records_normal(self, roles, role_mapping, records):
        logger.info('マッチング処理開始: roles=%s, records件数=%d', roles, len(records) if records else 0)
        matched = []
        for role in roles:
            mapped_remarks = role_mapping.get(role, []) if role_mapping else []
            logger.debug('role=%s, mapped_remarks=%s', role, mapped_remarks)
            for record in records:
                if hasattr(record, 'remarks') and record.remarks in mapped_remarks:
                    matched.append(record)
        logger.info('マッチング結果: matched件数=%d', len(matched))
        return matched
    def is_dekigata_related_record(self, record):
        # ...existing code from DictionaryManager.is_dekigata_related_record...
        pass
    def is_hinshitsu_related_record(self, record):
        # ...existing code from DictionaryManager.is_hinshitsu_related_record...
        pass
    def _best_match(self, text: str):
        """最も良いマッチのレコードとスコアを返す
        Args:
            text: OCRで検出されたテキスト
        Returns:
            (最良マッチレコード, スコア) のタプル
        """
        if not text or not getattr(self.manager, 'records', []):
            return None, 0
        # normalize関数を取得
        normalize = self.manager.__class__.__dict__.get('normalize', lambda x: x)
        try:
            from rapidfuzz import fuzz
        except ImportError:
            fuzz = self.manager.__class__.__dict__.get('fuzz', None)
        text_norm = normalize(text)
        best_record = None
        best_score = 0
        for record in getattr(self.manager, 'records', []):
            record_tokens = record.tokens()
            if not record_tokens:
                continue
            score = max(
                fuzz.partial_ratio(text_norm, token)
                for token in record_tokens
            )
            if score > best_score:
                best_record = record
                best_score = score
        return best_record, best_score
    def _legacy_match_text(self, text: str) -> dict:
        """従来の完全一致マッチング（フォールバック用）

        Args:
            text: OCRで検出されたテキスト

        Returns:
            マッチング結果（辞書タイプ: マッチしたエントリ）
        """
        result = {}
        for dict_type, entries in getattr(self.manager, 'dictionaries', {}).items():
            for entry in entries:
                if entry and entry in text:
                    result[dict_type] = entry
                    break
        return result

    def _extract_keywords(self, text: str) -> list:
        """テキストからキーワードを抽出

        Args:
            text: 解析するテキスト

        Returns:
            抽出されたキーワードのリスト
        """
        import re
        if not text:
            return []
        keywords = []
        special_patterns = re.findall(r'([A-Za-z]+\d*[\-=]+\d+|[A-Za-z]+\d*\-[A-Za-z]+\d*)', text)
        keywords.extend(special_patterns)
        temp_text = text
        for pattern in special_patterns:
            temp_text = temp_text.replace(pattern, "")
        words = re.split(r'[\s\.,;:()\[\]]+', temp_text)
        for word in words:
            if not word or len(word) < 2:
                continue
            keywords.append(word)
        return list(set(keywords))

    def _keyword_match(self, text: str) -> dict:
        """キーワードベースのマッチング
        テキストから抽出したキーワードと辞書レコードのキーワードが一致するかを調べる
        Args:
            text: OCRで検出されたテキスト
        Returns:
            マッチング結果（辞書タイプ: マッチしたエントリ）
        """
        if not text or not getattr(self.manager, 'records', []):
            return {}
        normalize = self.manager.__class__.__dict__.get('normalize', lambda x: x)
        text_keywords = self._extract_keywords(text)
        if not text_keywords:
            return {}
        text_keywords_norm = {normalize(kw) for kw in text_keywords}
        result = {}
        best_matches = {}
        for record in getattr(self.manager, 'records', []):
            record_dict = record.to_dict()
            record_keywords = record.keywords()
            record_keywords_norm = {normalize(kw) for kw in record_keywords}
            for dict_type, value in record_dict.items():
                if not value:
                    continue
                matches = text_keywords_norm.intersection(record_keywords_norm)
                if matches:
                    match_count = len(matches)
                    if dict_type not in best_matches or match_count > best_matches[dict_type][0]:
                        best_matches[dict_type] = (match_count, value)
        for dict_type, (_, value) in best_matches.items():
            result[dict_type] = value
        return result
