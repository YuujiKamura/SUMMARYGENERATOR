import logging
from PyQt6.QtWidgets import QFileDialog

def build_filtered_match_results(sorted_entries, match_results):
    filtered = {}
    for entry in sorted_entries:
        path = entry.image_path
        if path in match_results:
            filtered[path] = match_results[path]
    return filtered


def export_summary(entries, match_results, selected_cat, ascending, data_service, role_mapping, out_path=None, parent=None, cache_dir=None):
    logger = logging.getLogger(__name__)
    sorted_entries, _ = data_service.get_sorted_entries(entries, match_results, selected_cat, ascending)
    filtered_match_results = build_filtered_match_results(sorted_entries, match_results)
    logger.info('[export_summary_service] 件数: %d, filtered_match_results.keys: %s', len(filtered_match_results), list(filtered_match_results.keys())[:5])
    if out_path is None and parent is not None:
        out_path, _ = QFileDialog.getSaveFileName(parent, "Excelフォトブックの保存先を指定", "photobook.xlsx", "Excel Files (*.xlsx)")
        if not out_path:
            return
    from src.utils.excel_photobook_exporter import export_excel_photobook
    export_excel_photobook(
        filtered_match_results,
        {},  # image_roles（必要なら用意）
        getattr(data_service.dictionary_manager, 'records', []) if data_service.dictionary_manager else [],
        out_path,
        cache_dir=cache_dir
    )
    logger.info('[export_summary_service] Excel出力完了: %s', out_path)
