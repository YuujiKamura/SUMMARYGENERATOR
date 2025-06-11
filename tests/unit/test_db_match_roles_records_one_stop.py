import os
import tempfile
import pytest
import gc
from src.db_manager import init_db, ChainRecordManager, RoleMappingManager
from src.utils.chain_record_utils import ChainRecord
from src.record_matching_utils import match_roles_records_one_stop
import json

def setup_test_db():
    tmp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    db_path = tmp_db.name
    tmp_db.close()
    init_db(db_path)
    return db_path

def teardown_test_db(db_path):
    gc.collect()  # DBロック解除
    if os.path.exists(db_path):
        os.remove(db_path)

def test_match_roles_records_one_stop_thermometer():
    db_path = setup_test_db()
    try:
        # ChainRecord登録
        cr_id = ChainRecordManager.add_chain_record('温度測定', '品質管理写真', None, db_path=db_path)
        # role_mapping登録
        RoleMappingManager.add_or_update_role_mapping('温度測定', '{"roles": ["thermometer"], "match": "any"}', db_path=db_path)
        # DBから取得
        records = ChainRecordManager.get_all_chain_records(db_path=db_path)
        role_mapping = {row['role_name']: __import__('json').loads(row['mapping_json']) for row in RoleMappingManager.get_all_role_mappings(db_path=db_path)}
        # テスト用img_json
        img_json = {'roles': ['thermometer'], 'image_path': '/tmp/test1.jpg'}
        entry = match_roles_records_one_stop(img_json, role_mapping, [ChainRecord.from_dict(r) for r in records])
        remarks = [r.remarks for r in entry.chain_records if r is not None]
        assert '温度測定' in remarks
    finally:
        teardown_test_db(db_path)

def test_match_roles_records_one_stop_caption_board():
    db_path = setup_test_db()
    try:
        cr_id = ChainRecordManager.add_chain_record('出来形', '出来形管理写真', None, db_path=db_path)
        RoleMappingManager.add_or_update_role_mapping('出来形', '{"roles": ["caption_board_thermometer"], "match": "any"}', db_path=db_path)
        records = ChainRecordManager.get_all_chain_records(db_path=db_path)
        role_mapping = {row['role_name']: __import__('json').loads(row['mapping_json']) for row in RoleMappingManager.get_all_role_mappings(db_path=db_path)}
        img_json = {'roles': ['caption_board_thermometer'], 'image_path': '/tmp/test2.jpg'}
        entry = match_roles_records_one_stop(img_json, role_mapping, [ChainRecord.from_dict(r) for r in records])
        remarks = [r.remarks for r in entry.chain_records if r is not None]
        assert '出来形' in remarks
    finally:
        teardown_test_db(db_path)

def test_match_roles_records_one_stop_no_match():
    db_path = setup_test_db()
    try:
        cr_id = ChainRecordManager.add_chain_record('出来形', '出来形管理写真', None, db_path=db_path)
        RoleMappingManager.add_or_update_role_mapping('出来形', '{"roles": ["caption_board_thermometer"], "match": "any"}', db_path=db_path)
        records = ChainRecordManager.get_all_chain_records(db_path=db_path)
        role_mapping = {row['role_name']: __import__('json').loads(row['mapping_json']) for row in RoleMappingManager.get_all_role_mappings(db_path=db_path)}
        img_json = {'roles': ['not_exist_role'], 'image_path': '/tmp/test3.jpg'}
        entry = match_roles_records_one_stop(img_json, role_mapping, [ChainRecord.from_dict(r) for r in records])
        assert [r for r in entry.chain_records if r is not None] == []
    finally:
        teardown_test_db(db_path)

def import_role_mapping_json_to_db():
    import json
    from src.db_manager import RoleMappingManager
    with open('src/data/role_mapping.json', encoding='utf-8') as f:
        data = json.load(f)
    for remarks, mapping in data.items():
        if remarks.startswith('_'):  # コメント行はスキップ
            continue
        RoleMappingManager.add_or_update_role_mapping(remarks, json.dumps(mapping, ensure_ascii=False))

def test_db_realdata_role_matching():
    """
    本番DBのChainRecord/ロールマッピングを使い、img_jsonのrolesごとにマッチング結果（remarks）をassertする
    """
    import_role_mapping_json_to_db()
    from src.db_manager import ChainRecordManager, RoleMappingManager
    from src.utils.chain_record_utils import ChainRecord
    from src.record_matching_utils import match_roles_records_one_stop
    import json
    # 本番DBから全件取得（db_path指定なし）
    records = [ChainRecord.from_dict(r) for r in ChainRecordManager.get_all_chain_records()]
    role_mapping = {row['role_name']: json.loads(row['mapping_json']) for row in RoleMappingManager.get_all_role_mappings()}
    assert len(records) > 0, "ChainRecordがDBに存在しません"
    assert len(role_mapping) > 0, "ロールマッピングがDBに存在しません"
    # 代表的なrolesでマッチングテスト
    test_cases = [
        (['role_driver_backhoe_break'], ['剥取状況']),
        (['role_measurer_staff_setdown'], ['不陸整正出来形・全景', '不陸整正出来形・接写']),
        (['role_worker_emulsion_edge'], ['端部乳剤塗布状況']),
        (['role_measurer_thermometer'], []),  # 例: DBに該当がなければ空
    ]
    for roles, expected_remarks in test_cases:
        img_json = {'roles': roles, 'image_path': '/tmp/test_real.jpg'}
        entry = match_roles_records_one_stop(img_json, role_mapping, records)
        matched_remarks = [r.remarks for r in entry.chain_records if r is not None]
        for er in expected_remarks:
            assert er in matched_remarks 

def test_db_real_image_data_role_matching():
    """
    image_preview_cache_master.jsonの実データを使い、各画像のbboxesからrolesを抽出し、DBのChainRecord/ロールマッピングでマッチングしたremarksをlogs/match_roles_records_result.logにダンプする
    """
    import_role_mapping_json_to_db()
    from src.db_manager import ChainRecordManager, RoleMappingManager
    from src.utils.chain_record_utils import ChainRecord
    from src.record_matching_utils import match_roles_records_one_stop
    import json, os
    # DBから全件取得
    records = [ChainRecord.from_dict(r) for r in ChainRecordManager.get_all_chain_records()]
    role_mapping = {row['role_name']: json.loads(row['mapping_json']) for row in RoleMappingManager.get_all_role_mappings()}
    # 実データをロード
    with open('src/data/image_preview_cache_master.json', encoding='utf-8') as f:
        data = json.load(f)
    log_path = os.path.join('logs', 'match_roles_records_result.log')
    with open(log_path, 'w', encoding='utf-8') as logf:
        for entry in data:
            bboxes = entry.get('bboxes', [])
            roles = [b['role'] for b in bboxes if b.get('role')]
            if not roles:
                continue
            img_json = {'roles': roles, 'image_path': entry.get('image_path')}
            result = match_roles_records_one_stop(img_json, role_mapping, records)
            # matched_remarksの代わりにmatched_records（ChainRecord全体）をダンプ
            matched_records = [r.to_dict() if hasattr(r, 'to_dict') else dict(r) for r in result.chain_records if r is not None]
            logf.write(json.dumps({
                'image_path': entry.get('image_path'),
                'roles': roles,
                'records': matched_records
            }, ensure_ascii=False) + '\n')
            # 主要なロールが含まれていれば必ず1件以上マッチするはず
            if any(r for r in roles if r in role_mapping):
                assert len(matched_records) > 0, f"roles={roles} でマッチしない" 