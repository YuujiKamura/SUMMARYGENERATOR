"""
OCR Tools Module

OCR関連の機能を統合したモジュール
- DocumentAI による高精度OCR
- 自動キャッシュ機能
- 統一されたパス管理
"""

from .ocr_value_extractor import (
    process_image_json,
    init_documentai_engine,
    load_ocr_cache,
    save_ocr_cache,
    extract_texts_with_boxes_from_documentai_result
)

from .documentai_engine import DocumentAIOCREngine
from .ocr_config_loader import load_documentai_config, load_vision_config

# re-export location_inference helpers
# from .location_inference import (
#     build_time_lookup,
#     infer_survey_point_location,
#     is_incomplete_survey_point_location,
#     assign_inferred_survey_point_locations,
#     infer_location,
#     is_incomplete_location,
#     assign_inferred_locations,
# )

__version__ = "1.0.0"
__all__ = [
    'process_image_json',
    'init_documentai_engine',
    'load_ocr_cache',
    'save_ocr_cache',
    'extract_texts_with_boxes_from_documentai_result',
    'DocumentAIOCREngine',
    'load_documentai_config',
    'load_vision_config',
]
