import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))
import pytest
from src.record_matching_utils import match_roles_records

class DummyRecord:
    def __init__(self, remarks, roles=None):
        self.remarks = remarks
        self.roles = roles or []

def test_match_roles_records_all_match():
    # ロールマッピング: all
    mapping = {
        'test1': {'roles': ['role_a', 'role_b'], 'match': 'all'},
        'test2': {'roles': ['role_b'], 'match': 'all'},
    }
    records = [
        DummyRecord('test1'),
        DummyRecord('test2'),
    ]
    # rolesが両方含む場合は両方マッチする
    record = {'roles': ['role_a', 'role_b']}
    matched = match_roles_records(record, mapping, records)
    assert any(r.remarks == 'test1' for r in matched)
    assert any(r.remarks == 'test2' for r in matched)

def test_match_roles_records_any_match():
    # ロールマッピング: any
    mapping = {
        'test1': {'roles': ['role_a', 'role_b'], 'match': 'any'},
        'test2': {'roles': ['role_c'], 'match': 'any'},
    }
    records = [
        DummyRecord('test1'),
        DummyRecord('test2'),
    ]
    # role_aだけでもtest1がマッチ
    record = {'roles': ['role_a']}
    matched = match_roles_records(record, mapping, records)
    assert any(r.remarks == 'test1' for r in matched)
    assert not any(r.remarks == 'test2' for r in matched)

def test_match_roles_records_no_match():
    mapping = {
        'test1': {'roles': ['role_a'], 'match': 'all'},
    }
    records = [DummyRecord('test1')]
    record = {'roles': ['role_x']}
    matched = match_roles_records(record, mapping, records)
    assert matched == []

# unittest形式でも同じテストを追加
import unittest
class TestMatchRolesRecords(unittest.TestCase):
    def setUp(self):
        self.DummyRecord = DummyRecord

    def test_all_match(self):
        mapping = {
            'test1': {'roles': ['role_a', 'role_b'], 'match': 'all'},
            'test2': {'roles': ['role_b'], 'match': 'all'},
        }
        records = [self.DummyRecord('test1'), self.DummyRecord('test2')]
        record = {'roles': ['role_a', 'role_b']}
        matched = match_roles_records(record, mapping, records)
        self.assertTrue(any(r.remarks == 'test1' for r in matched))
        self.assertTrue(any(r.remarks == 'test2' for r in matched))

    def test_any_match(self):
        mapping = {
            'test1': {'roles': ['role_a', 'role_b'], 'match': 'any'},
            'test2': {'roles': ['role_c'], 'match': 'any'},
        }
        records = [self.DummyRecord('test1'), self.DummyRecord('test2')]
        record = {'roles': ['role_a']}
        matched = match_roles_records(record, mapping, records)
        self.assertTrue(any(r.remarks == 'test1' for r in matched))
        self.assertFalse(any(r.remarks == 'test2' for r in matched))

    def test_no_match(self):
        mapping = {'test1': {'roles': ['role_a'], 'match': 'all'}}
        records = [self.DummyRecord('test1')]
        record = {'roles': ['role_x']}
        matched = match_roles_records(record, mapping, records)
        self.assertEqual(matched, [])

if __name__ == '__main__':
    unittest.main()
