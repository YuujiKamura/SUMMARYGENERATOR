# このスクリプトはSummary Generator Widgetの起動専用です。
# 初期化処理やサービス層のセットアップは全てsrc/summary_generator_widget.py側に集約しています。
# ここではUIの起動のみを行います。

import sys
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from src.summary_generator_widget import SummaryGeneratorWidget

# --- ロガー設定 ---
# ・FileHandler : INFO 以上を logs/summary_generator_app.log へ詳細出力
# ・StreamHandler : WARNING 以上をターミナルへ（サマリーのみ）
logger = logging.getLogger()
logger.setLevel(logging.INFO)

fmt = '[%(asctime)s][%(levelname)s] %(message)s'
formatter = logging.Formatter(fmt)

# ファイル出力 (詳細)
file_handler = logging.FileHandler('logs/summary_generator_app.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

# コンソール出力 (サマリー)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)
console_handler.setFormatter(formatter)

# --- サマリー専用コンソールハンドラ (INFO) ---
class _SummaryFilter(logging.Filter):
    """メッセージがサマリーログ対象か判定して通過させるフィルタ"""
    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        msg = record.getMessage()
        return msg.startswith("===") or msg.startswith("[IMAGE]")

# Summary console shows message only (no timestamp)
summary_console = logging.StreamHandler()
summary_console.setLevel(logging.INFO)
summary_console.addFilter(_SummaryFilter())
summary_console.setFormatter(logging.Formatter('%(message)s'))

# 既存ハンドラをクリアして追加
logger.handlers.clear()
logger.addHandler(file_handler)
logger.addHandler(console_handler)
logger.addHandler(summary_console)

if __name__ == "__main__":
    logging.info("[STARTUP] アプリケーション起動開始")
    app = QApplication(sys.argv)
    
    logging.info("[STARTUP] SummaryGeneratorWidget初期化開始")
    w = SummaryGeneratorWidget()
    w.show()
    logging.info("[STARTUP] ウィジェット表示完了")

    # タイムアウト引数処理
    timeout_ms = None
    # --timeout=5 の形式を想定
    for arg in sys.argv:
        if arg.startswith("--timeout="):
            try:
                t = int(arg.split("=", 1)[1])
                timeout_ms = max(1, t) * 1000
                logging.info(f"[STARTUP] タイムアウト設定: {t}秒")
            except ValueError:
                pass

    # 旧互換: --test-mode は 10 秒
    if timeout_ms is None and "--test-mode" in sys.argv:
        timeout_ms = 10000
        logging.info("[STARTUP] テストモード: 10秒タイムアウト")

    if timeout_ms is not None:
        def timeout_handler():
            timeout_seconds = timeout_ms // 1000 if timeout_ms else 0
            logging.info(f"[STARTUP] タイムアウト({timeout_seconds}秒)でアプリケーション終了")
            app.quit()
        QTimer.singleShot(timeout_ms, timeout_handler)

    logging.info("[STARTUP] アプリケーションループ開始")
    sys.exit(app.exec())
