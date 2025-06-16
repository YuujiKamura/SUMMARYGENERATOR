# Credential Files

このディレクトリには認証情報ファイルを配置します。

## 必要なファイル

1. **visionapi-437405-0cd91b6d2db4.json** (または適切な名前のGoogleクレデンシャルファイル)
   - Google Cloud DocumentAI の認証情報
   - Google Cloud Console から取得したサービスアカウントキー

2. **documentai_config.json**
   - DocumentAI設定ファイル
   - `documentai_config.json.sample` をコピーして設定を更新

## セットアップ手順

1. `documentai_config.json.sample` を `documentai_config.json` にコピー
2. 適切な値に設定を更新：
   - `credential_path`: 認証ファイルの絶対パス
   - `project_id`: Google CloudプロジェクトID
   - `processor_id`: DocumentAI プロセッサID
   - `location`: リージョン（通常は "us"）

## セキュリティ注意事項

- 認証ファイルは `.gitignore` で除外されています
- これらのファイルは公開リポジトリにコミットしないでください
- 本番環境では環境変数や専用の認証情報管理システムを使用することを推奨します
