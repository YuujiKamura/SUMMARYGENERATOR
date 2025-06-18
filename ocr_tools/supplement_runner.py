"""supplement_runner.py
SurveyPoint 補完ロジックをクラスとして切り出したモジュール。
ImageEntryList を受け取り、場所・日付台数の補完を行い
`SurveyPoint.to_dict()` リストを返す。
"""
from __future__ import annotations

from typing import List, Optional
import os
import logging

# 長過ぎる import 行を分割
from .exif_utils import (
    get_capture_time_with_fallback,
    extract_image_number,
)
from .survey_point import SurveyPoint
# flake8: noqa: E501  # ドキュメント行の日本語は長くなりがちなため許容
from src.utils.image_entry import ImageEntryList

class SupplementRunner:
    """前後画像の文脈を利用して SurveyPoint を補完する実行クラス"""

    @staticmethod
    def run(image_entries: ImageEntryList, time_window_sec: int = 300) -> List[dict]:
        """補完を実行して dict リストを返す"""
        entries = image_entries.entries
        valid_entries = [e for e in entries if e.image_path]
        if not valid_entries:
            return []

        # sort by image number
        sorted_entries = sorted(
            valid_entries,
            key=lambda x: extract_image_number(x.image_path),
        )
        final_results: List[dict] = []

        # 単一パスで順方向に走査し、必要に応じて補完 ----------------
        for i, entry in enumerate(sorted_entries):
            sp = entry.survey_point
            # prev / next の取得
            prev_sp: Optional[SurveyPoint] = (
                sorted_entries[i - 1].survey_point if i > 0 else None
            )
            next_sp: Optional[SurveyPoint] = (
                sorted_entries[i + 1].survey_point if i + 1 < len(sorted_entries) else None
            )

            if sp is None:
                # OCR 失敗などで SurveyPoint が未生成の場合は空インスタンスを用意
                sp = SurveyPoint()

            if sp.isIncorrect():
                supplemented = SupplementRunner.supplement_by_closest(
                    sp,
                    prev_sp,
                    next_sp,
                    time_window_sec=time_window_sec,
                    keys=["location", "date_count"],
                )
                entry.survey_point = supplemented
                # 補完が行われた場合のみログ
                if "supplement_source" in supplemented.meta:
                    import logging as _lg
                    keys_changed = list(supplemented.inferred_values.keys())
                    _lg.info(
                        "[補完] %s ← %s | keys=%s | values=%s",
                        entry.filename or os.path.basename(entry.image_path),
                        supplemented.meta.get("supplement_source"),
                        keys_changed,
                        {k: supplemented.inferred_values[k] for k in keys_changed},
                    )
            # 補完の有無に関わらず dict 化して収集
            final_results.append(entry.survey_point.to_dict())

        return final_results

    @staticmethod
    def supplement_by_closest(
        sp: "SurveyPoint",
        prev_sp: Optional["SurveyPoint"],
        next_sp: Optional["SurveyPoint"],
        time_window_sec: int = 900,
        keys: Optional[list[str]] = None,
    ) -> "SurveyPoint":
        """`sp` を中心に前後の `SurveyPoint` を比較し、撮影時刻が近い方の
        情報で補完したコピーを返す。オリジナル `sp` は変更しない。

        * `time_window_sec` を超える差の場合は補完を行わず、そのままコピーを返す。
        * `keys` が省略された場合は ["location", "date_count"] を対象とする。
        """

        import copy

        if keys is None:
            keys = ["location", "date_count"]

        # deepcopy してから補完を適用
        new_sp = copy.deepcopy(sp)

        # capture_time が無い場合は補完しない
        if new_sp.capture_time is None:
            return new_sp

        # --- 型を float(timestamp) に正規化 --------------------------------
        def _to_ts(val):
            from datetime import datetime
            if val is None:
                return None
            if isinstance(val, (int, float)):
                return float(val)
            if isinstance(val, datetime):
                return val.timestamp()
            return None

        new_sp.capture_time = _to_ts(new_sp.capture_time)

        # 候補を距離付きで収集
        cands = []
        for neigh in (prev_sp, next_sp):
            if neigh and neigh.capture_time is not None:
                neigh_ts = _to_ts(neigh.capture_time)
                if neigh_ts is None:
                    continue
                diff = abs(neigh_ts - new_sp.capture_time)
                cands.append((diff, neigh))

        if not cands:
            # 補完元候補無し
            return new_sp

        # 最も近い候補
        diff_sec, best_neigh = min(cands, key=lambda t: t[0])
        if diff_sec > time_window_sec:
            # 設定された許容差を超える場合は補完しない
            return new_sp

        before = {k: getattr(new_sp, k, None) for k in keys}
        new_sp.supplement_from(best_neigh, keys)
        after = {k: getattr(new_sp, k, None) for k in keys}
        if before != after:
            logger = logging.getLogger(__name__)
            # 箇条書き・簡潔な形式で出力
            for k in keys:
                if before.get(k) != after.get(k):
                    logger.info(f"[補完] {getattr(new_sp, 'filename', '')} ← {getattr(best_neigh, 'filename', '')}: {after.get(k)}")
        return new_sp