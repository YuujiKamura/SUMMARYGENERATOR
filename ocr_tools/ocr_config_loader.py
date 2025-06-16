import json
import os
from typing import Dict

def load_vision_config(config_path: str) -> Dict:
    """
    Vision API用の設定ファイルを読み込む
    Args:
        config_path (str): config.jsonのパス
    Returns:
        dict: vision_api設定
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Vision API設定ファイルが見つかりません: {config_path}")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    return config.get('vision_api', {})

def load_documentai_config(config_path: str) -> Dict:
    """
    DocumentAI用の設定ファイルを読み込む
    Args:
        config_path (str): documentai_config.jsonのパス
    Returns:
        dict: DocumentAI設定
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"DocumentAI設定ファイルが見つかりません: {config_path}")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    return config
