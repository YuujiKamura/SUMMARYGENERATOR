"""supplement_runner.py
SurveyPoint 補完ロジックをクラスとして切り出したモジュール。
ImageEntryList を受け取り、場所・日付台数の補完を行い
`SurveyPoint.to_dict()` リストを返す。
"""
from __future__ import annotations

from typing import List, Optional
import os

from exif_utils import get_capture_time_with_fallback, extract_image_number
from survey_point import SurveyPoint
from src.utils.image_entry import ImageEntryList, ImageEntry

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
        sorted_entries = sorted(valid_entries, key=lambda x: extract_image_number(x.image_path))
        final_results: List[dict] = []

        # 順方向パス ------------------------------------------------------
        for i, entry in enumerate(sorted_entries):
            sp = entry.survey_point
            if sp is None:
                # create basic SurveyPoint
                capture = get_capture_time_with_fallback(entry.image_path)
                if capture is None:
                    try:
                        capture = os.path.getmtime(entry.image_path)
                    except:  # noqa: E722
                        pass
                sp = SurveyPoint(capture_time=capture)
                sp.filename = os.path.basename(entry.image_path)
                sp.image_path = entry.image_path

            # 前後候補
            prev_sp: Optional[SurveyPoint] = None
            next_sp: Optional[SurveyPoint] = None

            for j in range(i - 1, -1, -1):
                if sorted_entries[j].survey_point:
                    prev_sp = sorted_entries[j].survey_point
                    break
            for j in range(i + 1, len(sorted_entries)):
                if sorted_entries[j].survey_point:
                    next_sp = sorted_entries[j].survey_point
                    break

            supplemented = sp.supplemented_by_closest(prev_sp, next_sp, time_window_sec, keys=["location", "date_count"])
            # update lists
            entry.survey_point = supplemented
            sorted_entries[i].survey_point = supplemented
            final_results.append(supplemented.to_dict())

        # 逆方向パス（date_count 取りこぼし） -----------------------------
        for i in reversed(range(len(sorted_entries))):
            entry = sorted_entries[i]
            sp = entry.survey_point
            if sp is None or not sp.needs("date_count"):
                continue
            next_sp = None
            for j in range(i + 1, len(sorted_entries)):
                if sorted_entries[j].survey_point:
                    next_sp = sorted_entries[j].survey_point
                    break
            if next_sp and sp.supplement_from(next_sp, keys=["date_count"]):
                entry.survey_point = sp
                final_results[i] = sp.to_dict()

        return final_results 