import pytest
from src.image_entry import ImageEntry
from src.utils.chain_record_utils import ChainRecord
from src.record_matching_utils import match_roles_records_one_stop
from src.db_manager import ChainRecordManager, init_db

@pytest.fixture
def sample_records():
    # DBからChainRecordを取得
    return [ChainRecord.from_dict(r) for r in ChainRecordManager.get_all_chain_records()]

@pytest.fixture
def sample_role_mapping():
    # remarks→dict（roles, match）
    return {
        '温度測定': {'roles': ['thermometer'], 'match': 'any'},
        '出来形': {'roles': ['caption_board_dekigata'], 'match': 'any'},
    }

@pytest.fixture(autouse=True)
def setup_db_records():
    # DBを最新スキーマで初期化
    init_db()
    # 必要なChainRecordをDBに投入
    ChainRecordManager.add_chain_record(remarks='温度測定', photo_category='品質管理写真')
    ChainRecordManager.add_chain_record(remarks='出来形', photo_category='出来形管理写真')
    yield

def test_image_entry_from_cache_json_roles(sample_role_mapping, sample_records):
    # rolesが直接与えられる場合
    cache_json = {'roles': ['thermometer']}
    entry = ImageEntry.from_cache_json('dummy.jpg', cache_json, sample_role_mapping, sample_records)
    print(f"[TEST] chain_records: {[{'remarks': r.remarks, 'photo_category': r.photo_category} for r in entry.chain_records]}")
    assert len(entry.chain_records) == 1
    assert entry.chain_records[0].remarks == '温度測定'
    assert entry.chain_records[0].photo_category == '品質管理写真'

def test_image_entry_from_cache_json_bboxes(sample_role_mapping, sample_records):
    # bboxesからroles抽出
    cache_json = {'bboxes': [{'role': 'caption_board_dekigata'}]}
    entry = ImageEntry.from_cache_json('dummy2.jpg', cache_json, sample_role_mapping, sample_records)
    print(f"[TEST] chain_records: {[{'remarks': r.remarks, 'photo_category': r.photo_category} for r in entry.chain_records]}")
    assert len(entry.chain_records) == 1
    assert entry.chain_records[0].remarks == '出来形'
    assert entry.chain_records[0].photo_category == '出来形管理写真'

def test_image_entry_from_cache_json_empty(sample_role_mapping, sample_records):
    # rolesもbboxesも無い場合
    cache_json = {}
    entry = ImageEntry.from_cache_json('dummy3.jpg', cache_json, sample_role_mapping, sample_records)
    print(f"[TEST] chain_records: {entry.chain_records}")
    assert entry.chain_records == [] 