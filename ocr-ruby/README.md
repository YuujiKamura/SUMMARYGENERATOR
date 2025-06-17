# OCR Caption Board Processor (Ruby版)

ボード検出後の測点情報OCR処理と補完を行うRubyアプリケーション。

## 機能

- **DocumentAI OCR**: Google Cloud DocumentAI による高精度テキスト抽出
- **Survey Point補完**: 不完全な測点情報を近隣画像から自動補完
- **リアルタイム処理**: 各画像処理後に即座に補完処理を実行
- **デモモード**: DocumentAI APIなしでもダミーデータで動作確認可能

## セットアップ

### 1. 依存関係インストール

```bash
bundle install
```

### 2. DocumentAI設定（本番環境用）

#### 方法A: 設定ファイル使用

`config/document_ai.json` を編集：

```json
{
  "project_id": "your-gcp-project-id",
  "location": "us",
  "processor_id": "your-processor-id",
  "credentials_path": "/path/to/service-account-key.json"
}
```

#### 方法B: 環境変数使用

```bash
export GOOGLE_CLOUD_PROJECT_ID="your-project-id"
export DOCUMENT_AI_LOCATION="us"
export DOCUMENT_AI_PROCESSOR_ID="your-processor-id"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"
```

## ディレクトリ構成

```
ocr-ruby/
├── lib/
│   ├── ocr_processor.rb      # メインプロセッサー
│   ├── document_ai_client.rb # DocumentAI連携
│   ├── survey_point.rb       # 測点補完ロジック
│   ├── result_record.rb      # 結果レコード管理
│   └── exif_reader.rb        # EXIF情報読み取り
├── config/
│   └── document_ai.json      # DocumentAI設定
└── README.md
```
