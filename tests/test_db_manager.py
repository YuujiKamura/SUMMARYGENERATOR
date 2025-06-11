import os
import tempfile
import pytest
from pathlib import Path
import gc
from src import db_manager
import time
import json
from src.utils.chain_record_utils import load_chain_records

def setup_temp_db():
    tmpdir = tempfile.TemporaryDirectory()
    db_path = Path(tmpdir.name) / "test_yolo_data.db"
    db_manager.init_db(db_path)
    return tmpdir, db_path

def test_image_and_bbox_crud():
    tmpdir, db_path = setup_temp_db()
    try:
        img_id1 = db_manager.ImageManager.add_image("img1.jpg", "/path/img1.jpg", db_path=db_path)
        img_id2 = db_manager.ImageManager.add_image("img2.jpg", "/path/img2.jpg", db_path=db_path)
        img_id1_dup = db_manager.ImageManager.add_image("img1.jpg", "/path/img1.jpg", db_path=db_path)
        assert img_id1 == img_id1_dup
        images = db_manager.ImageManager.get_all_images(db_path=db_path)
        assert len(images) == 2
        bbox_id = db_manager.BBoxManager.add_bbox(img_id1, 1, "person", 0.9, 0, 0, 10, 10, "role1", db_path=db_path)
        bboxes = db_manager.BBoxManager.get_bboxes_for_image(img_id1, db_path=db_path)
        assert len(bboxes) == 1
        assert bboxes[0]["role"] == "role1"
    finally:
        del db_path
        gc.collect()
        tmpdir.cleanup()

def test_role_and_assignment():
    tmpdir, db_path = setup_temp_db()
    try:
        img_id = db_manager.ImageManager.add_image("img.jpg", "/path/img.jpg", db_path=db_path)
        role_id = db_manager.RoleManager.add_role("roleA", "desc", db_path=db_path)
        db_manager.RoleManager.assign_role_to_image(img_id, role_id, db_path=db_path)
        roles = db_manager.RoleManager.get_roles_for_image(img_id, db_path=db_path)
        assert any(r["name"] == "roleA" for r in roles)
    finally:
        del db_path
        gc.collect()
        tmpdir.cleanup()

def test_chain_record_and_assignment():
    tmpdir, db_path = setup_temp_db()
    try:
        img_id = db_manager.ImageManager.add_image("img.jpg", "/path/img.jpg", db_path=db_path)
        cr_id = db_manager.ChainRecordManager.add_chain_record("remarks1", "cat1", None, db_path=db_path)
        db_manager.ChainRecordManager.assign_chain_record_to_image(img_id, cr_id, db_path=db_path)
        crs = db_manager.ChainRecordManager.get_chain_records_for_image(img_id, db_path=db_path)
        assert any(c["remarks"] == "remarks1" for c in crs)
    finally:
        del db_path
        gc.collect()
        tmpdir.cleanup()

def test_role_mapping_crud():
    tmpdir, db_path = setup_temp_db()
    try:
        rid = db_manager.RoleMappingManager.add_or_update_role_mapping("roleX", '{"match": "any"}', db_path=db_path)
        mapping = db_manager.RoleMappingManager.get_role_mapping("roleX", db_path=db_path)
        assert mapping["role_name"] == "roleX"
        assert mapping["mapping_json"] == '{"match": "any"}'
        db_manager.RoleMappingManager.add_or_update_role_mapping("roleX", '{"match": "all"}', db_path=db_path)
        mapping2 = db_manager.RoleMappingManager.get_role_mapping("roleX", db_path=db_path)
        assert mapping2["mapping_json"] == '{"match": "all"}'
        db_manager.RoleMappingManager.delete_role_mapping("roleX", db_path=db_path)
        assert db_manager.RoleMappingManager.get_role_mapping("roleX", db_path=db_path) is None
    finally:
        del db_path
        gc.collect()
        tmpdir.cleanup()

def test_chain_record_and_role_mapping_logging():
    log_path = 'logs/A_dictionary_register.log'
    if os.path.exists(log_path):
        os.remove(log_path)
    tmpdir, db_path = setup_temp_db()
    try:
        # チェーンレコード登録
        cr_id = db_manager.ChainRecordManager.add_chain_record(
            remarks="test_remarks",
            photo_category="test_category",
            extra_json=json.dumps({"work_category": "catA", "type": "typeA", "subtype": "subA", "control": "ctrlA", "station": "stA"}),
            db_path=db_path
        )
        # ロールマッピング登録
        rm_id = db_manager.RoleMappingManager.add_or_update_role_mapping(
            "test_role",
            json.dumps({"roles": ["role1", "role2"], "match": "any"}, ensure_ascii=False),
            db_path=db_path
        )
        # 少し待つ（ファイル書き込みのタイミング対策）
        time.sleep(0.2)
        # ログファイル検証
        assert os.path.exists(log_path)
        with open(log_path, encoding='utf-8') as f:
            log_content = f.read()
        assert 'A_CHAINRECORD_REGISTER' in log_content
        assert 'test_remarks' in log_content
        assert 'A_ROLEMAPPING_REGISTER' in log_content
        assert 'test_role' in log_content
    finally:
        del db_path
        gc.collect()
        tmpdir.cleanup()

def test_load_real_chain_records_class():
    import json
    import time
    from src.utils.chain_record_utils import load_chain_records
    log_path = 'logs/A_dictionary_register.log'
    if os.path.exists(log_path):
        os.remove(log_path)
    tmpdir, db_path = setup_temp_db()
    try:
        # レコード単位でロード
        records_path = 'src/data/dictionaries/default_records.json'
        chain_records = load_chain_records(records_path)
        for rec in chain_records:
            db_manager.ChainRecordManager.add_chain_record(
                location=getattr(rec, 'location', None),
                controls=getattr(rec, 'controls', []),
                photo_category=rec.photo_category,
                work_category=getattr(rec, 'work_category', None) or getattr(rec, 'category', None),
                type_=getattr(rec, 'type', None),
                subtype=getattr(rec, 'subtype', None),
                remarks=rec.remarks,
                extra_json=json.dumps(getattr(rec, 'extra', {}), ensure_ascii=False),
                db_path=db_path
            )
        # ログ検証
        assert os.path.exists(log_path)
        with open(log_path, encoding='utf-8') as f:
            lines = [l for l in f if l.startswith('A_CHAINRECORD_REGISTER')]
        assert len(lines) == len(chain_records)
        for line, rec in zip(lines, chain_records):
            d = json.loads(line.split(' ', 1)[1])
            assert d['location'] == getattr(rec, 'location', None)
            assert d['controls'] == getattr(rec, 'controls', [])
            assert d['photo_category'] == rec.photo_category
            assert d['remarks'] == rec.remarks
    finally:
        del db_path
        gc.collect()
        tmpdir.cleanup() 