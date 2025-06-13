"""
SummaryDataServiceの初期化・DBセットアップ・マッチングテスト用CLI
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # src/ ディレクトリをパスに追加
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))  # プロジェクトルートも追加
from services.summary_data_service import SummaryDataService


def main():
    print("[CLI] SummaryDataService 初期化・DBリセット・データ投入・マッチングテスト開始")
    service = SummaryDataService()  # これだけで全自動で初期化・マッチング・S3ログ出力まで行う
    print("[CLI] SummaryDataService full_initialize完了（DB・データ・マッチング・ログ全出力）")

if __name__ == "__main__":
    main()
