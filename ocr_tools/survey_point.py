from __future__ import annotations

"""survey_point.py
SurveyPoint クラス
OCR で抽出された測点関連情報（場所・日付・台数など）を保持し、
近接画像からの補完判定・補完処理を簡潔に行うためのデータクラス。

location（測点）、date、count のほか、任意の key/value を格納出来る汎用構造。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import copy


@dataclass
class SurveyPoint:
    """OCR で抽出された測点情報を保持するデータクラス。

    必須: capture_time (Exif の撮影時刻; 秒単位)。

    任意:
        site_name   : 工区名
        point_no    : 測点 No.（路線中の測点番号）
        date        : 撮影日付 (YYYY-MM-DD など)
        filename    : ファイル名
        image_path  : 画像の絶対／相対パス
        values      : 台数・管理値など任意の追加情報
        inferred_values : 補完推定された値群
        meta        : bbox や OCR スキップ理由などメタ情報
    """

    capture_time: Optional[float] = None  # 秒単位の Unix タイムスタンプ (Exif)

    # --- optional fields ------------------------------------------------
    site_name: Optional[str] = None  # 工区名
    point_no: Optional[str] = None   # 測点 No.
    date: Optional[str] = None       # 日付文字列 (YYYY-MM-DD 等)

    filename: str = ""
    image_path: str = ""

    # 台数・管理値など任意の追加フィールドは values に格納する
    values: Dict[str, Any] = field(default_factory=dict)
    inferred_values: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)

    # capture_time が None でもインスタンス生成可能（補完・推定時に利用）

    # --- factory helpers -------------------------------------------------
    @staticmethod
    def from_raw(raw: Dict[str, Any]) -> "SurveyPoint":
        """OCR の生データ dict から SurveyPoint インスタンスを生成"""
        vals: Dict[str, Any] = {}
        # location
        if raw.get("location_value"):
            vals["location"] = raw["location_value"]

        # count (任意項目の例として台数を格納)
        date_val = raw.get("date_value")
        cnt_val = raw.get("count_value")
        if cnt_val:
            vals["count"] = cnt_val
        if date_val and cnt_val:
            vals["date_count"] = f"{date_val}|{cnt_val}"

        # metaをrawからそのまま引き継ぐ（判定根拠も含める）
        meta = raw.get("meta", {})
        if not meta:
            meta = {k: raw.get(k) for k in ("bbox", "ocr_skipped", "ocr_skip_reason")}
        meta["decision_source"] = meta.get("decision_source", "ocr")

        return SurveyPoint(
            capture_time=raw.get("capture_time"),
            site_name=raw.get("site_name"),
            point_no=raw.get("point_no"),
            date=raw.get("date_value"),
            filename=raw.get("filename", ""),
            image_path=raw.get("image_path", ""),
            values=vals,
            meta=meta,
        )

    # --- query helpers ---------------------------------------------------
    def has(self, key: str) -> bool:
        """key が values または inferred_values に存在するか判定"""
        return key in self.values or key in self.inferred_values

    def get(self, key: str) -> Optional[str]:
        """key に対応する値を取得（推定値を優先）"""
        return self.inferred_values.get(key) or self.values.get(key)

    def set_inferred(self, key: str, value: str):
        """補完値を設定。locationの場合は不完全な値も上書きする。"""
        # --- 値の設定 ---------------------------------------------------
        if key == "location":
            # location の場合は、不完全な値があっても補完する
            if not self.is_located():
                self.inferred_values[key] = value
        else:
            self.inferred_values[key] = value

        # --- decision_source の更新 -----------------------------------
        # 既存の decision_source に応じて更新する
        current_src: str = self.meta.get("decision_source", "")

        # nonboard → nonboard - inferred とする
        if current_src == "nonboard":
            self.meta["decision_source"] = "nonboard - inferred"
        # すでに nonboard - inferred なら変更不要
        elif current_src == "nonboard - inferred":
            pass
        else:
            # それ以外（ocr 等）は単に inferred
            self.meta["decision_source"] = "inferred"

    def needs(self, key: str) -> bool:
        """key の補完が必要か判定。不完全な情報も補完対象とする。"""
        if key == "location":
            # 場所情報は has() だけでなく、完全性もチェック
            return not self.is_located()
        elif key == "date_count":
            # date_count が無い、または不完全な場合も不正確とみなす
            if not self.has("date_count"):
                return True
            dc = self.inferred_values.get("date_count") or self.values.get("date_count")
            return not self._is_complete_date_count(dc)
        else:
            # その他のキー（date_count 等）は従来通り
            return not self.has(key)

    # --- completeness helpers ----------------------------------------
    @staticmethod
    def _is_complete_date_count(dc: str | None) -> bool:
        """date_count 文字列が "5/30|1台目" のように数値入り台数を含むか判定"""
        if not dc:
            return False
        parts = dc.split("|", 1)
        if len(parts) != 2:
            return False
        date_part, count_part = parts
        # 台数部に数字が含まれているか
        return bool(date_part.strip()) and bool(count_part) and any(ch.isdigit() for ch in count_part)

    # --- convenience -----------------------------------------------------
    def is_located(self) -> bool:
        """測点（location）が存在しかつ完全であるか判定"""
        if not self.has("location"):
            return False
        location_value = self.get("location")
        if location_value:
            try:
                from .location_inference import is_incomplete_survey_point_location
            except ImportError:
                from location_inference import is_incomplete_survey_point_location
            return not is_incomplete_survey_point_location(location_value)
        return False

    def isIncorrect(self) -> bool:
        """測点が不完全または不正確であるか判定"""
        # locationが存在しない、または不完全な場合
        if not self.has("location") or not self.is_located():
            return True
        # date_countが不完全な場合も不正確とみなす
        if not self.has("date_count"):
            return True
        return False

    # --- supplement ------------------------------------------------------
    def supplement_from(self, other: "SurveyPoint", keys: Optional[list[str]] = None):
        """other の値を欠損している keys に補完する。補完したら True を返す。"""
        if keys is None:
            keys = ["location", "date_count"]
        changed = False
        for k in keys:
            if self.needs(k) and other.has(k):
                value = other.get(k)
                if value is not None:
                    self.set_inferred(k, value)
                    changed = True
        return changed

    # -------------------------------------------------------------------
    def supplemented_by_closest(
        self,
        prev: Optional["SurveyPoint"],
        nxt: Optional["SurveyPoint"],
        time_window_sec: int = 900,
        keys: Optional[list[str]] = None,
    ) -> "SurveyPoint":
        """前後の SurveyPoint のうち撮影時刻が近い方の情報で補完したコピーを返す。

        self は変更せず、新しい SurveyPoint インスタンスを返す。
        time_window_sec を超える差の場合は補完を行わず、そのままコピーを返す。
        """

        if keys is None:
            keys = ["location", "date_count"]

        # deepcopy してから補完を適用
        new_sp = copy.deepcopy(self)

        # capture_time が無い場合は補完しない
        if new_sp.capture_time is None:
            return new_sp

        # 候補を距離付きで収集
        cands = []
        for neigh in (prev, nxt):
            if neigh and neigh.capture_time is not None:
                diff = abs(neigh.capture_time - new_sp.capture_time)
                cands.append((diff, neigh))

        if not cands:
            # 補完元候補無し
            return new_sp

        # 最も近い候補
        diff, best_neigh = min(cands, key=lambda t: t[0])
        if diff > time_window_sec:
            # 設定された許容差を超える場合は補完しない
            return new_sp

        # 実際に補完
        new_sp.supplement_from(best_neigh, keys)
        return new_sp

    # --- conversion back to dict ----------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """SurveyPoint を dict に変換（JSON への出力などに利用）"""
        raw = copy.deepcopy(self.meta)
        raw.update({
            "filename": self.filename,
            "image_path": self.image_path,
            "capture_time": self.capture_time,
        })
        # 基本項目
        if self.site_name:
            raw["site_name"] = self.site_name
        if self.point_no:
            raw["point_no"] = self.point_no
        if self.date:
            raw["date_value"] = self.date

        if "location" in self.values:
            raw["location_value"] = self.values["location"]
        if "location" in self.inferred_values:
            raw["inferred_location"] = self.inferred_values["location"]

        # date_count 処理（元の値と推定値の両方を考慮）
        date_count_str = self.inferred_values.get("date_count") or self.values.get("date_count")
        if date_count_str:
            try:
                date_val, cnt_val = date_count_str.split("|", 1)
                raw["date_value"], raw["count_value"] = date_val, cnt_val
            except ValueError:
                # 分割できない場合はそのまま格納
                pass

        # 推定された date_count も出力に含める
        if "date_count" in self.inferred_values:
            raw["inferred_date_count"] = self.inferred_values["date_count"]

        # metaを必ず含める
        raw["meta"] = copy.deepcopy(self.meta)
        return raw

    def get_display_value(self) -> str:
        """
        サマリーやUI表示用の代表値を返す。
        - matched_location_pairがあればその値
        - matched_date_pairとmatched_count_pairが両方あれば「日付 台数」
        - それ以外は従来通り
        """
        meta = self.meta or {}
        matched_location_pair = meta.get('matched_location_pair')
        matched_date_pair = meta.get('matched_date_pair')
        matched_count_pair = meta.get('matched_count_pair')
        if matched_location_pair:
            return matched_location_pair.get('value', '')
        elif matched_date_pair and matched_count_pair:
            # ペア由来の台数値が不完全な場合は補完された date_count を優先する
            date_val = matched_date_pair.get('value', '')
            count_val = matched_count_pair.get('value', '')
            if not any(ch.isdigit() for ch in str(count_val)):
                # 不完全とみなし、補完を確認
                dc = self.inferred_values.get('date_count')
                if dc and '|' in dc:
                    dv, cv = dc.split('|', 1)
                    return f"{dv} {cv}"
            return f"{date_val} {count_val}"
        # fallback: location, date_count, status, etc.
        loc = self.get('location')
        if loc:
            return loc
        dc = self.get('date_count')
        if dc:
            return dc
        return "情報なし"