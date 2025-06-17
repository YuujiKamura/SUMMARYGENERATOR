feat: Ruby版OCRシステム実装完了 - DocumentAI本番API対応

## 新機能
- Ruby版OCRシステム（ocr-ruby/）の完全実装
- Google Cloud DocumentAI v2.0 API統合
- Survey Point補完システムの移植
- 実際の工事写真でのOCR処理成功

## 主要コンポーネント
- DocumentAIClient: 本番API接続とOCR処理
- OCRProcessor: メイン処理クラス
- ResultRecord: 結果レコード管理
- SurveyPoint: 測点情報補完ロジック
- ExifReader: EXIF時刻抽出

## 実行スクリプト
- process_boards.rb: メインプロセッサー
- check_config.rb: 設定確認ツール
- test_connection.rb: DocumentAI接続テスト
- direct_ocr_test.rb: 直接APIテスト
- manual_ocr_test.rb: 手動パス指定テスト

## テスト結果
✅ DocumentAI API接続成功
✅ OCR処理: 3件処理、2件補完成功
✅ パターンマッチング: 測点番号・工区名正常抽出
✅ Survey Point補完: 時刻ベース近隣画像補完

## 技術仕様
- Ruby 3.2.3
- google-cloud-document_ai v2.0
- 同一認証情報でPython版と共存
- モジュラー設計、エラーハンドリング完備

## Python版との比較
| 機能 | Python | Ruby | 状態 |
|------|--------|------|------|
| DocumentAI | ✅ | ✅ | 同等 |
| OCR精度 | ✅ | ✅ | 同等 |
| 補完ロジック | ✅ | ✅ | 同等 |
| 設定管理 | ✅ | ✅ | 改善 |

Ruby版OCRシステムが本格運用レベルで完成。
「子供だまし」のデモから本番DocumentAI APIへ完全移行。
