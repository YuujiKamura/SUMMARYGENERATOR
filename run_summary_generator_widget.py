# このスクリプトはSummary Generator Widgetの起動専用です。
# 初期化処理やサービス層のセットアップは全てsrc/summary_generator_widget.py側に集約しています。
# ここではUIの起動のみを行います。

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer  # 追加
from src.summary_generator_widget import SummaryGeneratorWidget

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = SummaryGeneratorWidget()
    w.show()
    # テストモード時のみ10秒後に自動終了
    if "--test-mode" in sys.argv:
        QTimer.singleShot(10000, app.quit)
    sys.exit(app.exec())
