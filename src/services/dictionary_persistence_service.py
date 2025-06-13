from src.utils.chain_record_utils import ChainRecord
from src.db_manager import ChainRecordManager, RoleMappingManager
import json, os

class DictionaryPersistenceService:
    def __init__(self, manager, db_path=None):
        self.manager = manager
        self.db_path = db_path

    def load_dictionaries(self):
        # ...existing code from DictionaryManager.load_dictionaries...
        pass

    def save_dictionaries(self):
        # ...existing code from DictionaryManager.save_dictionaries...
        pass

    def set_project(self, project_name):
        # ...existing code from DictionaryManager.set_project...
        pass

    def reload_dictionaries(self):
        # ...existing code from DictionaryManager.reload_dictionaries...
        pass

    def _get_dictionary_file(self):
        # ...existing code from DictionaryManager._get_dictionary_file...
        pass
    def _get_records_file(self):
        # ...existing code from DictionaryManager._get_records_file...
        pass
    def _get_dictionary_dir(self):
        # ...existing code from DictionaryManager._get_dictionary_dir...
        pass
    def _ensure_dictionary_dir(self):
        # ...existing code from DictionaryManager._ensure_dictionary_dir...
        pass
