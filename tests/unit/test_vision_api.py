#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Google Cloud Vision APIの初期化に関するテスト
"""

import os
import sys
import json
import pytest
import tempfile
from unittest import mock
from pathlib import Path

# プロジェクトルートをパスに追加
current_dir = Path(__file__).parent.absolute()
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from app.controllers.ocr_controller import OcrThread
from app.utils.config_loader import load_config

# グローバル変数（テスト間で共有）
MOCK_VISION_CLIENT = mock.MagicMock()


# Google Cloud Vision APIのモック
@pytest.fixture
def mock_vision_api(monkeypatch):
    """Vision APIをモック化するフィクスチャ"""
    mock_vision = mock.MagicMock()
    mock_vision.ImageAnnotatorClient = mock.MagicMock(return_value=MOCK_VISION_CLIENT)
    
    mock_service_account = mock.MagicMock()
    mock_service_account.Credentials.from_service_account_file = mock.MagicMock(return_value=mock.MagicMock())
    
    monkeypatch.setattr('app.controllers.ocr_controller.VISION_AVAILABLE', True)
    monkeypatch.setattr('app.controllers.ocr_controller.vision', mock_vision)
    monkeypatch.setattr('app.controllers.ocr_controller.service_account', mock_service_account)
    
    return {
        'vision': mock_vision,
        'service_account': mock_service_account,
        'client': MOCK_VISION_CLIENT
    }


@pytest.fixture
def temp_config_file():
    """テスト用の一時的な設定ファイルを作成するフィクスチャ"""
    # 元の設定を読み込み
    original_config = load_config()
    
    # テスト用の一時ファイルを作成
    with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as temp_file:
        temp_file_path = temp_file.name
    
    # テスト終了後に元の設定に戻す
    yield temp_file_path
    
    # クリーンアップ
    if os.path.exists(temp_file_path):
        os.unlink(temp_file_path)


def create_credentials_file(path, valid=True):
    """テスト用の認証情報ファイルを作成"""
    # 有効な認証情報ファイルの内容
    valid_content = {
        "type": "service_account",
        "project_id": "test-project",
        "private_key_id": "test-key-id",
        "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCvJWBzPJrT/IHY\n-----END PRIVATE KEY-----\n",
        "client_email": "test@test-project.iam.gserviceaccount.com",
        "client_id": "123456789",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/test%40test-project.iam.gserviceaccount.com",
        "universe_domain": "googleapis.com"
    }
    
    # 無効な認証情報ファイルの内容
    invalid_content = {
        "project_id": "test-project",
        "invalid_key": "invalid_value"
    }
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(valid_content if valid else invalid_content, f)


class TestVisionAPI:
    """Vision APIの初期化テスト"""
    
    def test_init_with_no_credentials_file(self, mock_vision_api, monkeypatch):
        """認証情報ファイルが指定されていない場合のテスト"""
        # 設定を上書き
        test_config = {
            'vision_api': {
                'credentials_file': '',
                'use_api': True
            },
            'settings': {
                'retry_count': 3
            }
        }
        monkeypatch.setattr('app.controllers.ocr_controller.load_config', lambda: test_config)
        
        # DATA_DIRに認証情報ファイルが存在しないことを確認
        data_dir_path = mock.MagicMock(return_value=str(project_root / 'data'))
        monkeypatch.setattr('app.controllers.ocr_controller.DATA_DIR', data_dir_path)
        
        # ファイルが存在しないことをシミュレート
        monkeypatch.setattr('os.path.exists', lambda path: False)
        
        # OcrThreadを初期化
        ocr_thread = OcrThread([], None)
        
        # デフォルトの認証情報が使用されることを確認
        assert ocr_thread.vision_client == MOCK_VISION_CLIENT
        mock_vision_api['vision'].ImageAnnotatorClient.assert_called_once()
        mock_vision_api['service_account'].Credentials.from_service_account_file.assert_not_called()
    
    def test_init_with_valid_credentials_file(self, mock_vision_api, monkeypatch, temp_config_file):
        """有効な認証情報ファイルが指定されている場合のテスト"""
        # 有効な認証情報ファイルを作成
        create_credentials_file(temp_config_file, valid=True)
        
        # 設定を上書き
        test_config = {
            'vision_api': {
                'credentials_file': temp_config_file,
                'use_api': True
            },
            'settings': {
                'retry_count': 3
            }
        }
        monkeypatch.setattr('app.controllers.ocr_controller.load_config', lambda: test_config)
        
        # ファイルが存在することをシミュレート
        original_exists = os.path.exists
        monkeypatch.setattr('os.path.exists', lambda path: path == temp_config_file or original_exists(path))
        
        # OcrThreadを初期化
        ocr_thread = OcrThread([], None)
        
        # 認証情報ファイルからクライアントが初期化されることを確認
        assert ocr_thread.vision_client == MOCK_VISION_CLIENT
        mock_vision_api['service_account'].Credentials.from_service_account_file.assert_called_once_with(temp_config_file)
        mock_vision_api['vision'].ImageAnnotatorClient.assert_called_once()
    
    def test_init_with_invalid_credentials_file(self, mock_vision_api, monkeypatch, temp_config_file):
        """無効な認証情報ファイルが指定されている場合のテスト"""
        # 無効な認証情報ファイルを作成
        create_credentials_file(temp_config_file, valid=False)
        
        # 設定を上書き
        test_config = {
            'vision_api': {
                'credentials_file': temp_config_file,
                'use_api': True
            },
            'settings': {
                'retry_count': 3
            }
        }
        monkeypatch.setattr('app.controllers.ocr_controller.load_config', lambda: test_config)
        
        # ファイルが存在することをシミュレート
        original_exists = os.path.exists
        monkeypatch.setattr('os.path.exists', lambda path: path == temp_config_file or original_exists(path))
        
        # from_service_account_fileが例外を発生させるようにモック
        mock_vision_api['service_account'].Credentials.from_service_account_file.side_effect = Exception("Invalid credentials")
        
        # OcrThreadを初期化
        ocr_thread = OcrThread([], None)
        
        # 例外が発生し、vision_clientがNoneになることを確認
        assert ocr_thread.vision_client is None
        mock_vision_api['service_account'].Credentials.from_service_account_file.assert_called_once_with(temp_config_file)
    
    def test_api_disabled_in_config(self, mock_vision_api, monkeypatch):
        """設定でAPIが無効化されている場合のテスト"""
        # 設定を上書き
        test_config = {
            'vision_api': {
                'credentials_file': 'some_path',
                'use_api': False  # APIを無効化
            },
            'settings': {
                'retry_count': 3
            }
        }
        monkeypatch.setattr('app.controllers.ocr_controller.load_config', lambda: test_config)
        
        # OcrThreadを初期化
        ocr_thread = OcrThread([], None)
        
        # APIが無効なため、クライアントは初期化されないことを確認
        assert ocr_thread.vision_client is None
        mock_vision_api['vision'].ImageAnnotatorClient.assert_not_called()
        mock_vision_api['service_account'].Credentials.from_service_account_file.assert_not_called()
    
    def test_api_not_available(self, monkeypatch):
        """Vision APIが利用できない場合のテスト"""
        # Vision APIが利用できない状態をシミュレート
        monkeypatch.setattr('app.controllers.ocr_controller.VISION_AVAILABLE', False)
        
        # 設定を上書き
        test_config = {
            'vision_api': {
                'credentials_file': 'some_path',
                'use_api': True
            },
            'settings': {
                'retry_count': 3
            }
        }
        monkeypatch.setattr('app.controllers.ocr_controller.load_config', lambda: test_config)
        
        # OcrThreadを初期化
        ocr_thread = OcrThread([], None)
        
        # APIが利用できないため、クライアントは初期化されないことを確認
        assert ocr_thread.vision_client is None 