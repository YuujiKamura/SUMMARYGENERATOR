import os
import sys
import logging
from google.cloud import documentai_v1 as documentai
from google.oauth2 import service_account

class DocumentAIOCREngine:
    def __init__(self, project_id: str, location: str, processor_id: str, credentials_path: str):
        self.project_id = project_id
        self.location = location
        self.processor_id = processor_id
        self.credentials_path = credentials_path
        self.client = None
        try:
            credentials = service_account.Credentials.from_service_account_file(credentials_path)
            self.client = documentai.DocumentProcessorServiceClient(credentials=credentials)
        except Exception as e:
            logging.error(f"Document AIクライアントの初期化エラー: {e}")
            self.client = None
        self.processor_name = f"projects/{self.project_id}/locations/{self.location}/processors/{self.processor_id}"

    def extract_text(self, image_path: str) -> str:
        if not self.client:
            raise Exception("Document AIクライアントが初期化されていません")
        # 画像ファイルをバイナリで読み込み
        with open(image_path, "rb") as image_file:
            image_content = image_file.read()
        # リクエスト作成
        request = {
            "name": self.processor_name,
            "raw_document": {"content": image_content, "mime_type": "image/jpeg"}
        }
        # Document AI API呼び出し
        try:
            result = self.client.process_document(request=request)
            document = result.document
            # ページ全体のテキストを取得
            text = document.text if hasattr(document, 'text') else ''
            return text
        except Exception as e:
            logging.error(f"Document AI OCRエラー: {e}")
            raise
