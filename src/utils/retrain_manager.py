from typing import Dict, List, Optional
import os
import json
from pathlib import Path
from src.utils.path_manager import path_manager
from src.utils.chain_record import ChainRecord

class RetrainManager:
    def __init__(self):
        self.incorrect_entries: List[ChainRecord] = []
        self.retrain_data_dir = path_manager.get_retrain_data_dir()
        Path(self.retrain_data_dir).mkdir(parents=True, exist_ok=True)

    def add_incorrect_entry(self, record: ChainRecord):
        """不正解エントリーを追加"""
        self.incorrect_entries.append(record)

    def save_incorrect_entries(self):
        """不正解エントリーを保存"""
        if not self.incorrect_entries:
            return
        
        output_path = os.path.join(self.retrain_data_dir, "incorrect_entries.json")
        data = [record.to_dict() for record in self.incorrect_entries]
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_incorrect_entries(self) -> List[ChainRecord]:
        """保存された不正解エントリーを読み込み"""
        input_path = os.path.join(self.retrain_data_dir, "incorrect_entries.json")
        if not os.path.exists(input_path):
            return []
        
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return [ChainRecord.from_dict(entry) for entry in data]

    def prepare_retrain_dataset(self):
        """再学習用データセットの準備"""
        entries = self.load_incorrect_entries()
        if not entries:
            return
        
        # YOLOデータセット形式に変換
        dataset_dir = os.path.join(self.retrain_data_dir, "dataset")
        Path(dataset_dir).mkdir(parents=True, exist_ok=True)
        
        # TODO: YOLOデータセット形式への変換処理を実装 