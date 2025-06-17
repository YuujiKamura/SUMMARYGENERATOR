"""supplement_runner.py
SurveyPoint 補完ロジックをクラスとして切り出したモジュール。
ImageEntryList を受け取り、場所・日付台数の補完を行い
`SurveyPoint.to_dict()` リストを返す。
"""
from __future__ import annotations

from typing import List, Optional
import os

# 長過ぎる import 行を分割
from .exif_utils import (
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

        # 単一パスで順方向に走査し、必要に応じてその場で補完 ----------------
        for i, entry in enumerate(sorted_entries):
            sp = entry.survey_point
            # survey_point が存在し、不完全な場合のみ補完を試みる
            if sp is None:
                continue

            if hasattr(sp, "is_incomplete") and sp.is_incomplete():

                # 前後の survey_point を探索
                prev_sp: Optional[SurveyPoint] = None
                next_sp: Optional[SurveyPoint] = None

                # 前方向探索（i-1, i-2, ...）
                for j in range(i - 1, -1, -1):
                    cand_sp = sorted_entries[j].survey_point
                    if cand_sp is not None:
                        prev_sp = cand_sp
                        break

                # 後方向探索（i+1, i+2, ...）
                for j in range(i + 1, len(sorted_entries)):
                    cand_sp = sorted_entries[j].survey_point
                    if cand_sp is not None:
                        next_sp = cand_sp
                        break

                supplemented = SupplementRunner.supplement_by_closest(
                    sp,
                    prev_sp,
                    next_sp,
                    time_window_sec=time_window_sec,
                    keys=["location", "date_count"],
                )

                # update lists
                entry.survey_point = supplemented
                sorted_entries[i].survey_point = supplemented

            # ループ毎に現在の survey_point を結果に追加
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

        # 候補を距離付きで収集
        cands = []
        for neigh in (prev_sp, next_sp):
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